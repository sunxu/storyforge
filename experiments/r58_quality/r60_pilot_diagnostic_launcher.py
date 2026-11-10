"""Privacy-safe diagnostics for an existing R60 pilot runner; no model changes.

Run with /usr/bin/python3 -u /input/r60_pilot_diagnostic_launcher.py followed by
the original runner.py arguments. Do not print prompt/answer/case identifiers.
"""
from __future__ import annotations

import functools
import importlib.util
import json
import os
import resource
import subprocess
import sys
import threading
import time
from pathlib import Path

SCHEMA = "storyforge_r60_pilot_runtime_diag_safe_v1"
START = time.monotonic()
STOP = threading.Event()
LOCK = threading.Lock()
STATE = {"stage": "BOOT", "checkpoints_written": 0}
HEARTBEAT_SEC = 30
PHASES = {
    "hf_hub_download": "MODEL_DOWNLOAD",
    "snapshot_download": "MODEL_DOWNLOAD",
    "from_pretrained": "MODEL_OR_TOKENIZER_FETCH",
    "encode_chat": "TOKENIZER_ENCODING",
    "generate": "MODEL_GENERATION",
    "write_checkpoint": "CHECKPOINT_WRITE",
    "inference": "INFERENCE_FUNCTION",
}


def emit(event: str, **data: object) -> None:
    print(json.dumps({
        "schema": SCHEMA, "event": event,
        "elapsed_sec": round(time.monotonic() - START, 1),
        "private_values_emitted": False, **data,
    }, sort_keys=True, separators=(",", ":")), flush=True)


def set_stage(stage: str) -> None:
    with LOCK:
        STATE["stage"] = stage
    emit("STAGE", stage=stage)


def process_stats() -> dict:
    usage = resource.getrusage(resource.RUSAGE_SELF)
    cpu = os.times()
    return {
        "peak_rss_mib": round(usage.ru_maxrss / 1024, 1),
        "process_cpu_sec": round(cpu.user + cpu.system, 1),
    }


def gpu_stats() -> dict:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, check=True, timeout=3,
        ).stdout.strip().splitlines()
        if not out:
            return {"gpu_probe": "NO_DATA"}
        parts = [int(x.strip()) for x in out[0].split(",")]
        if len(parts) != 3:
            return {"gpu_probe": "INVALID"}
        return {"gpu_util_pct": parts[0], "gpu_used_mib": parts[1],
                "gpu_total_mib": parts[2]}
    except (OSError, ValueError, subprocess.SubprocessError):
        return {"gpu_probe": "UNAVAILABLE"}


def descendant_stats() -> dict:
    """Aggregate Linux child processes using /proc numeric fields only.

    Never disclose process arguments, executable paths, environment or names.
    Include descendants (not the current Python parent process).
    """
    try:
        clock = os.sysconf("SC_CLK_TCK")
        page = os.sysconf("SC_PAGE_SIZE")
        nodes = {}
        for entry in os.scandir("/proc"):
            if not entry.name.isdecimal():
                continue
            try:
                # /proc/PID/stat has a parenthesized comm which may contain
                # spaces or right parens. Do not print or retain that text.
                statline = Path(entry.path, "stat").read_text()
                fields = statline.rsplit(")", 1)[1].strip().split()
                if len(fields) < 22:
                    continue
                pid = int(entry.name)
                ppid = int(fields[1])
                state = fields[0]
                cpu_ticks = int(fields[11]) + int(fields[12])
                rss_pages = int(fields[21])
                nodes[pid] = (ppid, state, cpu_ticks, rss_pages)
            except (OSError, ValueError, IndexError):
                continue
        living = {os.getpid()}
        descendants = set()
        for _ in range(8):
            new = {pid for pid, (ppid, _, _, _) in nodes.items()
                   if ppid in living and pid not in living}
            if not new:
                break
            living.update(new)
            descendants.update(new)
        counts = {}
        for pid in descendants:
            state = nodes[pid][1]
            state = state if state in "RSDTZI" else "OTHER"
            counts[state] = counts.get(state, 0) + 1
        return {
            "descendant_count": len(descendants),
            "descendant_cpu_sec": round(sum(nodes[p][2] for p in descendants) / clock, 1),
            "descendant_rss_mib": round(sum(nodes[p][3] for p in descendants) * page / 1048576, 1),
            "descendant_states": counts,
        }
    except (OSError, ValueError):
        return {"descendant_probe": "UNAVAILABLE"}


def safe_stack_phase() -> str:
    # Expose allowlisted function labels only; never paths, line text, locals,
    # private case identifiers, stack traces, URLs or model outputs.
    ident = threading.main_thread().ident
    frame = sys._current_frames().get(ident) if ident is not None else None
    while frame is not None:
        label = PHASES.get(frame.f_code.co_name)
        if label is not None:
            return label
        frame = frame.f_back
    return "OTHER_OR_NATIVE_WAIT"


def heartbeat() -> None:
    while not STOP.wait(HEARTBEAT_SEC):
        with LOCK:
            snapshot = dict(STATE)
        emit("HEARTBEAT", **snapshot, stack_phase=safe_stack_phase(),
             **process_stats(), **descendant_stats(), **gpu_stats())


def attach_hooks(worker: object) -> None:
    original_read = worker.read_input

    @functools.wraps(original_read)
    def read_input(*args, **kwargs):
        set_stage("READ_INPUT")
        rows = original_read(*args, **kwargs)
        emit("INPUT_VERIFIED", cases_total=len(rows))
        return rows

    worker.read_input = read_input
    original_write = worker.write_checkpoint

    @functools.wraps(original_write)
    def write_checkpoint(*args, **kwargs):
        result = original_write(*args, **kwargs)
        with LOCK:
            STATE["checkpoints_written"] += 1
            count = STATE["checkpoints_written"]
        emit("CHECKPOINT_WRITTEN", count=count)
        return result

    worker.write_checkpoint = write_checkpoint
    original_inference = worker.inference

    @functools.wraps(original_inference)
    def inference(*args, **kwargs):
        set_stage("GPU_INFERENCE_INIT_OR_GENERATE")
        emit("INFERENCE_ENTER", **process_stats(), **gpu_stats())
        result = original_inference(*args, **kwargs)
        set_stage("INFERENCE_RETURNED")
        emit("INFERENCE_SUMMARY", cases_total=result.get("cases_total", 0),
             cases_completed=result.get("cases_completed", 0),
             quote_repair_attempts=result.get("quote_repair_attempts", 0),
             quote_repair_successes=result.get("quote_repair_successes", 0))
        return result

    worker.inference = inference
    # New traced runner copies call only this allowlisted callback. Old
    # unmodified runners remain supported by the launcher.
    worker._r60_diag_event = set_stage


def main() -> int:
    source = Path(__file__).resolve().parent / "runner.py"
    if source.is_symlink() or not source.is_file():
        emit("BOOT_HOLD", reason_code="RUNNER_NOT_REGULAR")
        return 42
    os.environ["PYTHONUNBUFFERED"] = "1"
    emit("BOOT", heartbeat_sec=HEARTBEAT_SEC,
         python_version=f"{sys.version_info.major}.{sys.version_info.minor}")
    thread = threading.Thread(target=heartbeat, daemon=True)
    thread.start()
    try:
        spec = importlib.util.spec_from_file_location("r60_pilot_runner", str(source))
        if spec is None or spec.loader is None:
            emit("BOOT_HOLD", reason_code="RUNNER_IMPORT_SPEC_HOLD")
            return 42
        sys.path.insert(0, str(source.parent))
        worker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(worker)
        if not all(callable(getattr(worker, name, None)) for name in
                   ("main", "inference", "read_input", "write_checkpoint")):
            emit("BOOT_HOLD", reason_code="RUNNER_API_HOLD")
            return 42
        attach_hooks(worker)
        set_stage("RUNNER_MAIN")
        result = int(worker.main())
        emit("RUNNER_EXIT", exit_code=result, **process_stats())
        return result
    except Exception:  # noqa: BLE001 - intentionally redact private exception details
        emit("LAUNCHER_HOLD", reason_code="RUNTIME_EXCEPTION_REDACTED")
        return 42
    finally:
        STOP.set()
        thread.join(timeout=2)


if __name__ == "__main__":
    raise SystemExit(main())
