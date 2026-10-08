"""Auditable HF Jobs entrypoint for the StoryForge smoke gate."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path("/workspace")
DATA = ROOT / "datasets/v0.3"
CACHE = ROOT / "cache"

class Runner:
    def __init__(self, run_dir: Path) -> None:
        self.run_dir = run_dir
        self.commands: list[str] = []
        self.stdout = (run_dir / "stdout.log").open("a", encoding="utf-8")
        self.stderr = (run_dir / "stderr.log").open("a", encoding="utf-8")

    def close(self) -> None:
        self.stdout.close()
        self.stderr.close()

    def run(self, cmd: list[str], *, check: bool = True, name: str | None = None) -> subprocess.CompletedProcess[str]:
        print("+", " ".join(cmd), flush=True)
        self.commands.append(" ".join(cmd))
        (self.run_dir / "command.txt").write_text("\n".join(self.commands) + "\n", encoding="utf-8")
        try:
            result = subprocess.run(cmd, text=True, capture_output=True, check=False)
        except OSError as exc:
            message = f"{type(exc).__name__}: {exc}\n"
            self.stderr.write(message)
            self.stderr.flush()
            if name:
                (self.run_dir / name).write_text(message, encoding="utf-8")
            if check:
                raise
            return subprocess.CompletedProcess(cmd, 127, "", message)
        self.stdout.write(result.stdout)
        self.stderr.write(result.stderr)
        self.stdout.flush()
        self.stderr.flush()
        if name:
            (self.run_dir / name).write_text(result.stdout + result.stderr, encoding="utf-8")
        if check and result.returncode:
            raise RuntimeError(f"command exited {result.returncode}: {' '.join(cmd)}")
        return result

    def stream(self, cmd: list[str]) -> int:
        print("+", " ".join(cmd), flush=True)
        self.commands.append(" ".join(cmd))
        (self.run_dir / "command.txt").write_text("\n".join(self.commands) + "\n", encoding="utf-8")
        with (self.run_dir / "train.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
            assert process.stdout is not None and process.stderr is not None
            lock = threading.Lock()

            def drain(stream, destination, terminal):
                for line in stream:
                    print(line, end="", file=terminal, flush=True)
                    with lock:
                        destination.write(line)
                        log.write(line)
                        destination.flush()
                        log.flush()

            threads = [threading.Thread(target=drain, args=(process.stdout, self.stdout, sys.stdout)),
                       threading.Thread(target=drain, args=(process.stderr, self.stderr, sys.stderr))]
            for thread in threads:
                thread.start()
            code = process.wait()
            for thread in threads:
                thread.join()
            return code


def collect_environment(runner: Runner, *, before: bool, require_gpu: bool) -> None:
    suffix = "before" if before else "after"
    for name, command in {
        "hostname": ["hostname"], "uname": ["uname", "-a"], "nvidia-smi": ["nvidia-smi"],
        "gpu-info": ["nvidia-smi", "--query-gpu=name,memory.total,memory.free", "--format=csv,noheader,nounits"],
        "python": [sys.executable, "--version"], "df": ["df", "-h", str(ROOT)],
        "disk-info": ["df", "-Pk", str(ROOT)], "free": ["free", "-h"],
    }.items():
        result = runner.run(command, check=False, name=f"{name}-{suffix}.txt")
        if name == "nvidia-smi" and require_gpu and result.returncode:
            raise RuntimeError("nvidia-smi failed during GPU environment qualification")
        if name == "gpu-info" and require_gpu and before:
            rows = [line.split(",") for line in result.stdout.splitlines() if line.strip()]
            if result.returncode or not rows or int(rows[0][1].strip()) < 70000 or int(rows[0][2].strip()) < 70000:
                raise RuntimeError(f"GPU has less than expected 80 GiB total/free VRAM: {result.stdout.strip()!r}")
        if name == "disk-info" and require_gpu and before and result.returncode == 0:
            available_kib = int(result.stdout.splitlines()[-1].split()[3])
            if available_kib < 80 * 1024 * 1024:
                raise RuntimeError(f"less than 80 GiB free disk space: {available_kib} KiB")


def count_rows(path: Path) -> int:
    return sum(bool(line.strip()) for line in path.open(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def training_evidence(output: Path) -> dict[str, object]:
    states = list(output.rglob("trainer_state.json"))
    if not states:
        raise RuntimeError("training finished but trainer_state.json is missing")
    state_path, state = max(((path, json.loads(path.read_text(encoding="utf-8"))) for path in states),
                            key=lambda item: int(item[1].get("global_step", 0)))
    step = int(state.get("global_step", 0))
    if step < 3:
        raise RuntimeError(f"training global_step is {step}, expected at least 3")
    history = state.get("log_history", [])
    losses = [item["loss"] for item in history if item.get("loss") is not None]
    eval_losses = [item["eval_loss"] for item in history if item.get("eval_loss") is not None]
    if not losses or not all(math.isfinite(float(value)) for value in losses):
        raise RuntimeError("no finite training loss in trainer_state.json")
    if not eval_losses or not all(math.isfinite(float(value)) for value in eval_losses):
        raise RuntimeError("no finite eval_loss in trainer_state.json")
    checkpoint = state_path.parent
    weights = [path for path in checkpoint.glob("adapter_model*") if path.is_file()]
    if not weights:
        raise RuntimeError("adapter weights are missing")
    adapter_config = checkpoint / "adapter_config.json"
    if not adapter_config.is_file():
        raise RuntimeError(f"adapter_config.json is missing beside {state_path}")
    return {"global_step": step, "loss": losses[-1], "eval_loss": eval_losses[-1], "checkpoint": str(state_path),
            "adapter": str(checkpoint), "adapter_weights": str(weights[-1])}


def make_inference_input(source: Path, destination: Path) -> None:
    """Create one generation-only prompt, never exposing the Gold assistant target."""
    row = next((json.loads(line) for line in source.open(encoding="utf-8") if line.strip()), None)
    if not row:
        raise RuntimeError("validation dataset is empty")
    messages = row["messages"]
    if len(messages) < 2 or messages[-2]["role"] != "user" or messages[-1]["role"] != "assistant":
        raise RuntimeError("validation sample does not end in user/Gold assistant")
    prompt = [{"role": m["role"], "content": m["content"]} for m in messages[:-1]]
    destination.write_text(json.dumps({"messages": prompt}, ensure_ascii=False) + "\n", encoding="utf-8")


def check_inference_result(path: Path) -> None:
    rows = [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]
    if not rows or not any(isinstance(row.get("response"), str) and row["response"].strip() for row in rows):
        raise RuntimeError("inference result has no non-empty response")


class GpuMonitor:
    def __init__(self) -> None:
        self.stop = threading.Event()
        self.peak_mib = 0
        self.thread = threading.Thread(target=self._poll, daemon=True)

    def _poll(self) -> None:
        while not self.stop.is_set():
            try:
                result = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                                        capture_output=True, text=True, check=False)
            except OSError:
                return
            if result.returncode == 0:
                values = [int(line.strip()) for line in result.stdout.splitlines() if line.strip().isdigit()]
                self.peak_mib = max(self.peak_mib, max(values, default=0))
            self.stop.wait(1.0)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_args):
        self.stop.set()
        self.thread.join(timeout=3)

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--git-commit", required=True)
    args = parser.parse_args()
    job_id = os.environ.get("JOB_ID")
    if not job_id or "/" in job_id or job_id in {".", ".."}:
        raise RuntimeError("Missing or invalid HF Jobs JOB_ID; refusing shared output path")
    run_dir = ROOT / "runs" / job_id
    if run_dir.exists():
        raise FileExistsError(f"Refusing to overwrite an existing run: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=False)
    runner = Runner(run_dir)
    status = "FAIL"
    details = [f"git_commit: {args.git_commit}", "config: configs/qwen38-27b-qlora-smoke.yaml",
               "base_model: Qwen/Qwen3.8-27B", "dataset: data/compiled/v0.3 train+validation",
               "runner: scripts/hf_job_runner.py", "guard: scripts/hf_smoke_guard.py",
               "audit: scripts/hf_label_mask_audit.py"]
    after_collected = False
    started = time.monotonic()
    os.environ["CUDA_VISIBLE_DEVICES"] = "0"
    CACHE.mkdir(parents=True, exist_ok=True)
    os.environ["HF_HOME"] = str(CACHE / "huggingface")
    os.environ["PIP_CACHE_DIR"] = str(CACHE / "pip")
    os.environ["PYTHONUNBUFFERED"] = "1"
    # Reuse package wheels/cache, but use the container's compatible PyTorch.
    try:
        collect_environment(runner, before=True, require_gpu=not args.audit_only)
        runner.run([sys.executable, "-m", "pip", "install", "-U",
                    "ms-swift==4.5.3", "transformers==5.16.1", "bitsandbytes",
                    "qwen-vl-utils>=0.0.14", "decord"])
        runner.run([sys.executable, "-m", "pip", "freeze"], name="pip-freeze.txt")
        runner.run([sys.executable, "-c",
                    "import importlib.metadata as m; print({n: m.version(n) for n in ('ms-swift','transformers','bitsandbytes','decord')})"],
                   name="versions.txt")
        from importlib.metadata import version
        (run_dir / "environment.json").write_text(json.dumps({
            "python": sys.version,
            "ms_swift": version("ms-swift"),
            "transformers": version("transformers"),
            "bitsandbytes": version("bitsandbytes"),
            "decord": version("decord"),
            "job_id": os.environ.get("JOB_ID"),
            "git_commit": args.git_commit,
        }, indent=2), encoding="utf-8")
        script = ROOT / "scripts/prepare_sft.py"
        for split in ("train", "validation"):
            source = DATA / f"{split}.jsonl"
            if not source.is_file():
                raise FileNotFoundError(f"missing {source}")
            runner.run([sys.executable, str(script), "--source", str(source),
                        "--output", str(run_dir / f"{split}.jsonl")])
        config = ROOT / "configs/qwen38-27b-qlora-smoke.yaml"
        runner.run([sys.executable, str(ROOT / "scripts/hf_cpu_preflight.py"), "--data", str(run_dir), "--config", str(config)])
        audit = ROOT / "scripts/hf_label_mask_audit.py"
        for split in ("train", "validation"):
            path = run_dir / f"{split}.jsonl"
            runner.run([sys.executable, str(audit), "--dataset", str(path), "--model", "Qwen/Qwen3.8-27B",
                        "--samples", str(count_rows(path)), "--config", str(config),
                        "--config", str(ROOT / "configs/qwen38-27b-qlora-v0.1.yaml")])
        details += ["dataset preflight: PASS", "train label audit: PASS", "validation label audit: PASS"]
        if args.audit_only:
            collect_environment(runner, before=False, require_gpu=False)
            after_collected = True
            status = "PASS"
            details.append("audit_only: true")
            return
        cmd = ["swift", "sft", str(config), "--dataset", str(run_dir / "train.jsonl"),
               "--val_dataset", str(run_dir / "validation.jsonl"), "--output_dir", str(run_dir / "output"),
               "--max_steps", "3", "--max_length", "16384", "--save_only_model", "false",
               "--loss_scale", "last_round", "--custom_register_path", str(ROOT / "scripts/hf_smoke_guard.py")]
        with GpuMonitor() as monitor:
            code = runner.stream(cmd)
        if code:
            raise RuntimeError(f"swift exited {code}")
        evidence = training_evidence(run_dir / "output")
        adapter = Path(str(evidence["adapter"]))
        inference_input = run_dir / "infer-input.jsonl"
        make_inference_input(run_dir / "validation.jsonl", inference_input)
        inference_output = run_dir / "inference-results.jsonl"
        runner.run(["swift", "infer", "--model", "Qwen/Qwen3.8-27B", "--use_hf", "true", "--adapters", str(adapter),
                    "--val_dataset", str(inference_input), "--val_dataset_sample", "1", "--infer_backend", "transformers",
                    "--torch_dtype", "bfloat16", "--quant_method", "bnb", "--quant_bits", "4",
                    "--bnb_4bit_compute_dtype", "bfloat16", "--result_path", str(inference_output)])
        check_inference_result(inference_output)
        collect_environment(runner, before=False, require_gpu=True)
        after_collected = True
        (run_dir / "SUCCESS").write_text("Smoke training, adapter reload and inference passed\n", encoding="utf-8")
        details += ["gpu: CUDA_VISIBLE_DEVICES=0", f"training_steps: {evidence['global_step']}",
                    f"final_loss: {evidence['loss']}",
                    f"eval_loss: {evidence['eval_loss']}", f"peak_vram_mib: {monitor.peak_mib}",
                    f"adapter: {adapter}", "adapter reload/inference: PASS"]
        status = "PASS"
    except Exception as exc:
        details.append(f"error: {type(exc).__name__}: {exc}")
        raise
    finally:
        if not after_collected:
            try:
                collect_environment(runner, before=False, require_gpu=False)
            except OSError as exc:
                details.append(f"after_environment_error: {exc}")
        details.append(f"elapsed_seconds: {time.monotonic() - started:.1f}")
        details.append("warnings: inspect stdout.log and stderr.log")
        environment = []
        for label, path in (("config_sha256", ROOT / "configs/qwen38-27b-qlora-smoke.yaml"),
                            ("runner_sha256", ROOT / "scripts/hf_job_runner.py"),
                            ("guard_sha256", ROOT / "scripts/hf_smoke_guard.py"),
                            ("audit_sha256", ROOT / "scripts/hf_label_mask_audit.py")):
            if path.exists():
                details.append(f"{label}: {sha256(path)}")
        gpu_info = run_dir / "gpu-info-before.txt"
        if gpu_info.exists():
            details.append("gpu_info: " + " ".join(gpu_info.read_text(encoding="utf-8").split()))
        for name in ("hostname", "uname", "nvidia-smi", "gpu-info", "python", "df", "disk-info", "free"):
            for phase in ("before", "after"):
                path = run_dir / f"{name}-{phase}.txt"
                if path.exists():
                    environment.append(f"## {name} {phase}\n{path.read_text(encoding='utf-8')}")
        (run_dir / "environment.txt").write_text("\n\n".join(environment), encoding="utf-8")
        details.append("status: " + status)
        (run_dir / "summary.md").write_text((status + "\n" + "\n".join(details) + "\n"), encoding="utf-8")
        runner.close()
        print("Artifacts at", run_dir, flush=True)

if __name__ == "__main__":
    main()
