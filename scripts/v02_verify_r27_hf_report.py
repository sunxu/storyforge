"""Strict read-only R27 HF 117-row result verifier; does not grant training approval."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

MODEL_REVISION = "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0"
EXPECTED_DATASET_SHA256 = "cdecc311f05e2c700f1038f3afca09c889ff681d4ef55dc18dc7426c9d14a92a"
EXPECTED_RUN_STATUS = "REMOTE_FINAL_INPUT_DIAGNOSTIC_ONLY"
APPROVAL = "PENDING_NOT_APPROVED"
HEXDIGEST = re.compile(r"^[a-f0-9]{64}$")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify(report_path: Path, archive_path: Path) -> dict:
    report_bytes = report_path.read_bytes()
    report = json.loads(report_bytes)
    if not isinstance(report, dict):
        raise ValueError("R27 report must be a JSON object")
    if (report.get("status") != EXPECTED_RUN_STATUS
            or report.get("admission") != APPROVAL
            or report.get("training_performed") is not False
            or report.get("expected_candidates") != 117
            or report.get("checked") != 117
            or report.get("passed") != 117
            or report.get("source_sha256") != EXPECTED_DATASET_SHA256):
        raise ValueError("R27 result/admission/source is not the expected completed diagnostic")
    versions = report.get("versions")
    if not isinstance(versions, dict) or versions.get("ms-swift") != "4.5.3":
        raise ValueError("R27 ms-swift runtime version is not the pinned audited version")
    with zipfile.ZipFile(archive_path) as archive:
        matches = [
            name for name in archive.namelist()
            if name.endswith("/output/r27_private_candidate_117_NOT_APPROVED.jsonl")
        ]
        if len(matches) != 1:
            raise ValueError("R27 source JSONL missing or ambiguous")
        data = archive.read(matches[0])
    if sha256(data) != EXPECTED_DATASET_SHA256:
        raise ValueError("R27 dataset bytes are not the frozen candidate")
    originals = [json.loads(line) for line in data.splitlines() if line.strip()]
    if len(originals) != 117 or len({row["id"] for row in originals}) != 117:
        raise ValueError("R27 source count/unique IDs failure")
    if any(row.get("metadata", {}).get("dataset_admission") != "NOT_APPROVED" for row in originals):
        raise ValueError("R27 source has been promoted without approval")
    expected = {row["id"]: row["metadata"]["source_story_id"] for row in originals}
    results = report.get("rows")
    if not isinstance(results, list) or len(results) != 117:
        raise ValueError("R27 report lacks exactly 117 results")
    observed = set()
    transformers_counts = []
    native_counts = []
    total_supervised = 0
    renderer_differences = 0
    for entry in results:
        if not isinstance(entry, dict):
            raise ValueError("malformed per-row result")
        candidate_id = entry.get("candidate_id")
        if candidate_id not in expected or candidate_id in observed:
            raise ValueError("unexpected or duplicated result candidate")
        observed.add(candidate_id)
        if entry.get("story_id") != expected[candidate_id]:
            raise ValueError(f"story group mismatch: {candidate_id}")
        if entry.get("status") != "ACTUAL_LAST_ROUND_INTERNAL_PASS":
            raise ValueError(f"non-PASS collator record: {candidate_id}")
        if entry.get("error"):
            raise ValueError(f"collator error present: {candidate_id}")
        digest = entry.get("label_digest")
        if not isinstance(digest, str) or HEXDIGEST.fullmatch(digest) is None:
            raise ValueError(f"missing label evidence digest: {candidate_id}")
        t, n, s = (
            entry.get("transformers_token_count"),
            entry.get("ms_swift_token_count"),
            entry.get("supervised_tokens"),
        )
        if (any(type(k) is not int for k in (t, n, s))
                or min(t, n, s) < 1 or t > 16384 or n > 16384 or s > n):
            raise ValueError(f"invalid token counts: {candidate_id}")
        if type(entry.get("renderers_identical")) is not bool:
            raise ValueError(f"missing renderer comparison: {candidate_id}")
        renderer_differences += not entry["renderers_identical"]
        transformers_counts.append(t)
        native_counts.append(n)
        total_supervised += s
    if observed != set(expected):
        raise ValueError("R27 report missing source IDs")
    return {
        "status": "R27_REMOTE_REPORT_INTEGRITY_VERIFIED_ONLY",
        "report_sha256": sha256(report_bytes),
        "source_sha256": EXPECTED_DATASET_SHA256,
        "rows": len(results),
        "unique_stories": len(set(expected.values())),
        "ms_swift_min": min(native_counts),
        "ms_swift_max": max(native_counts),
        "ms_swift_total": sum(native_counts),
        "transformers_max": max(transformers_counts),
        "total_supervised": total_supervised,
        "renderer_differences": renderer_differences,
        "admission": APPROVAL,
        "training_performed": False,
        "limitations": [
            "Recorded result only; per-token labels are not in this JSON and are not independently replayed.",
            "No content/age approval, unseen heldout, linked-world split, or formal training release.",
        ],
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--report", required=True, type=Path)
    p.add_argument("--r27-archive", type=Path, required=True)
    args = p.parse_args()
    outcome = verify(args.report, args.r27_archive)
    print(json.dumps(outcome, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
