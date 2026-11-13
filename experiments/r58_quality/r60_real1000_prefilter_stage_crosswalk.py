"""Read-only prefilter-to-HF-stage identity gate for frozen REAL1000.

Reuses frozen_pool and hf_blind_stage.verified_stage; does not rewrite the
existing staged inputs or create a filtered stage. Returns SAFE counts only.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import r60_real1000_offline_prefilter as prefilter
import r60_real_private_batch as private
import r60_real_quality_batch as quality

from storyforge_gold_quality import hf_blind_stage

SCHEMA = "storyforge_r60_prefilter_hf_stage_crosswalk_safe_v1"


class Hold(ValueError):
    pass


def read_record(path: Path, size_limit: int) -> dict:
    """Parse existing immutable receipts; accept legacy literal backslash-n."""
    raw = private.read_private(path, size_limit)
    if raw.endswith(b"\\\\n"):
        raw = raw[:-2]
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise Hold("PREFILTER_RECORD_TYPE_HOLD")
    return parsed


def verify_receipts(directory: Path, cases: list[dict], pool_sha: str) -> dict:
    private.private_dir(directory, create=False)
    summary = read_record(directory / prefilter.OUTPUT, quality.MAX_CASE_BYTES)
    if (summary.get("schema") != prefilter.SCHEMA
            or summary.get("pool_sha256") != pool_sha
            or summary.get("cases_total") != prefilter.EXPECTED
            or summary.get("quality_evaluated") is not False
            or summary.get("train_admitted") != 0
            or not isinstance(summary.get("pages"), list)
            or len(summary["pages"]) !=
            prefilter.EXPECTED // prefilter.PAGE_SIZE):
        raise Hold("PREFILTER_MANIFEST_BINDING_HOLD")

    recorded = []
    for index, entry in enumerate(summary["pages"], 1):
        filename = f"R60_REAL1000_PREFILTER_PAGE_{index:04d}_PRIVATE.json"
        if not isinstance(entry, dict) or entry.get("name") != filename:
            raise Hold("PREFILTER_PAGE_INDEX_HOLD")
        page = read_record(directory / filename, 100_000)
        if (page.get("schema") != prefilter.SCHEMA
                or page.get("pool_sha256") != pool_sha
                or page.get("page_index") != index
                or entry.get("sha256") != private.digest(page)
                or not isinstance(page.get("rows"), list)
                or len(page["rows"]) != prefilter.PAGE_SIZE):
            raise Hold("PREFILTER_PAGE_SHA_HOLD")
        recorded.extend(page["rows"])

    if len(recorded) != prefilter.EXPECTED:
        raise Hold("PREFILTER_CASE_COUNT_HOLD")
    for index, (row, case) in enumerate(zip(recorded, cases, strict=True), 1):
        if (not isinstance(row, dict)
                or row.get("position") != index
                or row.get("case_key") != case["case_key"]
                or row.get("history_messages_sha256") !=
                case["history_messages_sha256"]
                or row.get("assistant_target_sha256") !=
                case["assistant_target_sha256"]):
            raise Hold("PREFILTER_ROW_IDENTITY_HOLD")
    expected = prefilter.classify_cases(cases)
    if recorded != expected or summary.get("safe") != prefilter.summarize(expected):
        raise Hold("PREFILTER_DECISION_DRIFT_HOLD")
    return summary["safe"]


def audit(expand_dir: Path, prefilter_dir: Path, stage_dir: Path) -> dict:
    safe = {
        "schema": SCHEMA,
        "status": "PREFILTER_STAGE_CROSSWALK_HOLD",
        "model_requests": 0, "gpu_started": False,
        "database_modified": False, "quality_v1_admitted": 0,
        "train_admitted": 0, "private_values_emitted": False,
    }
    try:
        cases, pool_sha = quality.frozen_pool(expand_dir)
        status = verify_receipts(prefilter_dir, cases, pool_sha)
        manifest, _crosswalk = hf_blind_stage.verified_stage(
            stage_dir, pool_sha, cases,
        )
        if manifest.get("count") != prefilter.EXPECTED:
            raise Hold("STAGE_COUNT_HOLD")
        states = Counter(row["state"] for row in prefilter.classify_cases(cases))
        return {
            **safe,
            "status": (
                "PREFILTER_STAGE_ALL_ELIGIBLE__CONTENT_REVIEW_PENDING"
                if states["STRUCTURE_PASS"] == prefilter.EXPECTED
                else "PREFILTER_STAGE_SUBSET_REQUIRED__NO_MODEL_REQUEST"
            ),
            "cases_total": prefilter.EXPECTED,
            "prefilter_pass": status["structure_pass"],
            "prefilter_excluded": status["excluded"],
            "prefilter_context_hold": status["context_hold"],
            "stage_identity_verified": prefilter.EXPECTED,
            "staged_model_reviews_verified": False,
        }
    except (OSError, ValueError, TypeError, KeyError, IndexError):
        return safe


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expand-dir", type=Path, required=True)
    parser.add_argument("--prefilter-dir", type=Path, required=True)
    parser.add_argument("--stage-dir", type=Path, required=True)
    args = parser.parse_args()
    safe = audit(args.expand_dir, args.prefilter_dir, args.stage_dir)
    print(json.dumps(safe, sort_keys=True))
    return 42 if safe["status"] == "PREFILTER_STAGE_CROSSWALK_HOLD" else 0


if __name__ == "__main__":
    raise SystemExit(main())
