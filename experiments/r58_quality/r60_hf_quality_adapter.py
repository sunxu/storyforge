"""R60 thin adapter: frozen 1000 Owner-private candidates -> generic HF Quality Pipeline.

No local model, API calls, Supabase, R50 body, GPU submission or training.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import r60_real_quality_batch as local_batch
import r60_real_private_batch as g1

try:
    from storyforge_gold_quality import hf_blind_stage
    from storyforge_gold_quality import hf_literary_review
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
    from storyforge_gold_quality import hf_blind_stage
    from storyforge_gold_quality import hf_literary_review

SAFE_SCHEMA = "storyforge_r60_hf_quality_adapter_safe_v1"


def frozen_source(directory: Path) -> tuple[list[dict], str]:
    """Use the existing verified R60 1000-case gate, never a raw JSONL import."""
    cases, pool_sha = local_batch.frozen_pool(directory)
    if len(cases) != 1000:
        raise hf_blind_stage.StageError("R60_1000_FROZEN_SOURCE_REQUIRED")
    return cases, pool_sha


def prepare(expand_dir: Path, stage_dir: Path,
            model_a: str, revision_a: str,
            model_b: str, revision_b: str) -> dict:
    cases, pool_sha = frozen_source(expand_dir)
    if (not stage_dir.is_absolute() or stage_dir.parent != g1.BASE
            or not stage_dir.name.startswith("r60-hf-quality-")):
        raise hf_blind_stage.StageError("R60_STAGE_PRIVATE_PATH_HOLD")
    result = hf_blind_stage.stage(
        stage_dir, cases, pool_sha, Path(hf_literary_review.__file__),
        model_a, revision_a, model_b, revision_b)
    return {"schema": SAFE_SCHEMA, **{k: v for k, v in result.items()
                                      if k != "schema"}}


def audit(expand_dir: Path, stage_dir: Path) -> dict:
    cases, pool_sha = frozen_source(expand_dir)
    if (not stage_dir.is_absolute() or stage_dir.parent != g1.BASE
            or not stage_dir.name.startswith("r60-hf-quality-")):
        raise hf_blind_stage.StageError("R60_STAGE_PRIVATE_PATH_HOLD")
    result = hf_blind_stage.audit(stage_dir, pool_sha, cases)
    return {"schema": SAFE_SCHEMA, **{k: v for k, v in result.items()
                                      if k != "schema"}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    stage = sub.add_parser("prepare")
    stage.add_argument("--expand-dir", type=Path, required=True)
    stage.add_argument("--stage-dir", type=Path, required=True)
    stage.add_argument("--model-a", required=True)
    stage.add_argument("--revision-a", required=True)
    stage.add_argument("--model-b", required=True)
    stage.add_argument("--revision-b", required=True)
    view = sub.add_parser("audit")
    view.add_argument("--expand-dir", type=Path, required=True)
    view.add_argument("--stage-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.mode == "prepare":
            receipt = prepare(
                args.expand_dir, args.stage_dir, args.model_a,
                args.revision_a, args.model_b, args.revision_b)
        else:
            receipt = audit(args.expand_dir, args.stage_dir)
        print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - safe-only on private data errors
        allowed = {"R60_1000_FROZEN_SOURCE_REQUIRED",
                   "R60_STAGE_PRIVATE_PATH_HOLD"}
        code = str(exc) if isinstance(exc, hf_blind_stage.StageError) and (
            str(exc) in allowed or str(exc).startswith(("PRIVATE_STAGE_", "STAGE_",
                                                        "SOURCE_", "MODEL_REVISION_",
                                                        "REVIEWER_RUNNER_",
                                                        "FROZEN_SOURCE_"))) else (
            "R60_HF_ADAPTER_SOURCE_OR_IO_HOLD")
        print(json.dumps({
            "schema": SAFE_SCHEMA, "status": "HF_QUALITY_ADAPTER_HOLD",
            "reason_code": code, "quality_v1_admitted": 0,
            "training_authorized": False, "gpu_started": False,
            "r50_body_accessed": False, "private_values_emitted": False,
        }, ensure_ascii=False, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
