"""R60 GLM: frozen private-runner Snapshot -> CPU Replay integration probe.

The input is pinned and private; an error is deliberately synthesized from
genuine source-backed excerpts. No model weights, vLLM, HF, external network,
GPU, checkpoint changes, or private stdout. All scratch output is 0700 and
automatically destroyed before returning. Proves replay interoperability,
not actual model review quality.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from r60_generation_snapshot import GenerationSnapshotStore
from r60_glm4_literal_repair_cpu_probe import synthetic_punctuation_case
from r60_glm4_snapshot_replay import (
    MODEL,
    REV,
    SCHEMA,
    frozen,
    load_original_rows,
    summarize,
)


class PreflightHold(ValueError):
    pass


STAGES = frozenset({
    "FROZEN_IMPORT", "PINNED_INPUT", "QUOTE_FIXTURE",
    "FROZEN_VALIDATION", "SNAPSHOT_WRITE",
    "CPU_REPLAY", "ASSERTIONS",
})


def probe(runner: Path, source: Path, *, on_stage=None) -> dict:
    def phase(name: str):
        if name not in STAGES:
            raise PreflightHold("UNKNOWN_PHASE_HOLD")
        if on_stage is not None:
            on_stage(name)

    phase("FROZEN_IMPORT")
    worker = frozen(runner)
    phase("PINNED_INPUT")
    rows = load_original_rows(source, worker)
    row = rows[0]
    phase("QUOTE_FIXTURE")
    try:
        exact, distorted = synthetic_punctuation_case(row["target_text"])
    except Exception as exc:
        raise PreflightHold("SYNTHETIC_QUOTE_CANDIDATE_HOLD") from exc
    if not exact or distorted in row["target_text"]:
        raise PreflightHold("SYNTHETIC_QUOTE_CANDIDATE_HOLD")

    schema = worker.response_schema()
    scores = {key: 4 for key in schema["properties"]["scores"]["properties"]}
    flags = {key: False
             for key in schema["properties"]["severe_flags"]["properties"]}
    response = {
        "decision": "HOLD", "scores": scores, "severe_flags": flags,
        "specific_source_quotes": [row["visible_history"][0]["content"][:24]],
        "specific_target_quotes": [distorted],
        "literary_quality_notes": "合成CPU测试：仅验证快照与离线回放机制",
        "uncertainty": "这是合成测试，不是质量审核结果。",
    }

    phase("FROZEN_VALIDATION")
    # Before writing any synthetic snapshot, prove the original frozen runner
    # rejects it for the expected quote reason (not some unrelated shape error).
    try:
        worker.checkpoint_record(1, row, response, MODEL, REV)
    except worker.ReviewError as exc:
        if str(exc) != "MODEL_NONEXACT_QUOTE_HOLD":
            raise PreflightHold("FROZEN_INITIAL_REASON_HOLD") from None
    else:
        raise PreflightHold("FROZEN_EXPECTED_REJECTION_MISSING_HOLD")

    phase("SNAPSHOT_WRITE")
    with tempfile.TemporaryDirectory(prefix="r60-glm-snapshot-cpu-") as temporary:
        scratch = Path(temporary)
        private_snapshots = scratch / "snapshots"
        private_snapshots.mkdir(mode=0o700)
        generated = json.dumps(response, ensure_ascii=False, separators=(",", ":"))
        events = []
        store = GenerationSnapshotStore(
            private_snapshots, worker=worker, model=MODEL, revision=REV,
            runner_sha256=hashlib.sha256(runner.read_bytes()).hexdigest(),
            emit=lambda event, **data: events.append((event, data)),
        )
        store.start(1, row)
        fake = SimpleNamespace(
            generate=lambda *args, **kwargs: [SimpleNamespace(
                outputs=[SimpleNamespace(text=generated, finish_reason="stop")])])
        store.wrap(fake).generate(["synthetic prompt"])
        phase("CPU_REPLAY")
        report = summarize(SimpleNamespace(
            runner=runner, input=source, snapshots=private_snapshots,
            output=scratch / "report.safe.json"))
        phase("ASSERTIONS")
        actual = report["cases"][0]
        if (len(events) != 1 or report["replayed_cases"] != 1
                or actual["original_frozen"]["technical_status"] != "REPLAY_FAILED"
                or actual["literal_experiment"]["technical_status"] != "REPLAY_VALIDATED"
                or actual["literal_experiment"]["quality_decision"] != "HOLD"
                or report["quality_v1_admitted"] != 0
                or report["training_authorized"]):
            raise PreflightHold("SNAPSHOT_REPLAY_INTEGRATION_HOLD")

    return {
        "schema": SCHEMA,
        "status": "GLM_FROZEN_SNAPSHOT_CPU_REPLAY_PREFLIGHT_PASS",
        "frozen_runner_used": True, "pinned_source_sha_verified": True,
        "model_inference_calls": 0, "gpu_started": False,
        "private_values_emitted": False, "scratch_removed": True,
        "strict_original_quote_rejected": True,
        "literal_cpu_replay_validated": True,
        "quality_v1_admitted": 0, "training_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", required=True, type=Path)
    parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args()
    stage = "FROZEN_IMPORT"
    def on_stage(name):
        nonlocal stage
        stage = name
    try:
        print(json.dumps(probe(args.runner, args.input, on_stage=on_stage), sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - no private exception messages
        reason = str(exc) if type(exc) is PreflightHold and str(exc) in {
            "SYNTHETIC_QUOTE_CANDIDATE_HOLD",
            "FROZEN_INITIAL_REASON_HOLD",
            "FROZEN_EXPECTED_REJECTION_MISSING_HOLD",
            "SNAPSHOT_REPLAY_INTEGRATION_HOLD",
        } else "STAGE_EXCEPTION_REDACTED"
        print(json.dumps({
            "schema": SCHEMA, "status": "GLM_FROZEN_SNAPSHOT_CPU_REPLAY_PREFLIGHT_HOLD",
            "stage": stage, "reason_code": reason,
            "private_values_emitted": False, "gpu_started": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
