"""Create a private, blank Owner Evidence worksheet from verified R59 staging.

Copies only candidate identity/pin fields into a private template. Every
attestation and review reference remains null; this is explicitly NOT evidence,
approval, Quality-v1 admission, or training authorization.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import stat
from pathlib import Path

from gold_source_context_stage import _create_only, _private_file, _read_rows
from quality_v1 import EVIDENCE, sha

SCHEMA = "storyforge-r59-owner-evidence-template-safe-v1"
STAGE_SCHEMA = "storyforge-quality-v1-source-staging-private-v1"
STAGE_STATUS = "SOURCE_CONTEXT_STAGED__QUALITY_REVIEW_PENDING"
HEX = re.compile(r"^[0-9a-f]{64}$")
NEGATIVE_EVIDENCE = (
    "known_protected_overlap",
    "final_heldout_overlap",
    "protected_test_body_accessed",
)
SEVERE_FLAGS = ("serious_player_agency", "hard_fact_or_ban", "safety_exclusion")


class TemplateHold(ValueError):
    pass


def build_template(staged_rows, staged_sha: str, source_context_sha: str):
    if HEX.fullmatch(staged_sha or "") is None or HEX.fullmatch(source_context_sha or "") is None:
        raise TemplateHold("STAGING_PIN_INVALID")
    rows = []
    seen = set()
    for stage in staged_rows:
        if not isinstance(stage, dict):
            raise TemplateHold("STAGING_ROW_INVALID")
        if (stage.get("schema") != STAGE_SCHEMA or stage.get("status") != STAGE_STATUS):
            continue
        cid = stage.get("case_id")
        if not isinstance(cid, str) or not cid or cid in seen:
            raise TemplateHold("STAGING_CASE_ID_INVALID_OR_DUPLICATE")
        seen.add(cid)
        for key in ("target_sha256",):
            if HEX.fullmatch(stage.get(key) or "") is None:
                raise TemplateHold("STAGING_TARGET_PIN_INVALID")
        for key in ("story_id", "session_id"):
            if not isinstance(stage.get(key), str) or not stage[key]:
                raise TemplateHold("STAGING_IDENTITY_INVALID")
        rows.append({
            "case_id": cid,
            "target_sha256": stage["target_sha256"],
            "story_id": stage["story_id"],
            "session_id": stage["session_id"],
            "staged_file_sha256": staged_sha,
            "source_context_file_sha256": source_context_sha,
            "source_version_sha256": None,
            "world_graph_sha256": None,
            "world_component_id": None,
            "split": None,
            "reviewer_a_evidence_ref": None,
            "reviewer_b_evidence_ref": None,
            "reviewer_a_severe_flags": {key: None for key in SEVERE_FLAGS},
            "evidence": {key: None for key in (*EVIDENCE, *NEGATIVE_EVIDENCE)},
        })
    if not rows:
        raise TemplateHold("NO_STAGED_CANDIDATES")
    rows.sort(key=lambda row: row["case_id"])
    return rows


def run(staged_path: Path, receipt_path: Path, output_dir: Path):
    staged_raw = _private_file(staged_path, 160 * 1024 * 1024)
    receipt_raw = _private_file(receipt_path, 1024 * 1024)
    try:
        receipt = json.loads(receipt_raw)
    except (ValueError, UnicodeError):
        raise TemplateHold("STAGING_RECEIPT_INVALID") from None
    staged_sha = sha(staged_raw)
    if (receipt.get("schema") != "storyforge-gold-quality-supabase-source-stage-safe-v1"
            or receipt.get("staged_file_sha256") != staged_sha):
        raise TemplateHold("STAGING_RECEIPT_MISMATCH")
    source_context_sha = receipt.get("source_context_file_sha256")
    rows = build_template(_read_rows(staged_raw), staged_sha, source_context_sha)
    if output_dir.exists() or output_dir.is_symlink():
        raise TemplateHold("OUTPUT_EXISTS")
    if output_dir.resolve().is_relative_to(Path.cwd().resolve()):
        raise TemplateHold("OUTPUT_INSIDE_REPO")
    if (not output_dir.parent.is_dir() or output_dir.parent.is_symlink()
            or stat.S_IMODE(output_dir.parent.stat().st_mode) != 0o700):
        raise TemplateHold("OUTPUT_PARENT_INVALID")
    output_dir.mkdir(mode=0o700)
    try:
        payload = b"".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
            + b"\\n" for row in rows
        )
        digest = _create_only(output_dir / "OWNER_CASE_EVIDENCE_TEMPLATE_PRIVATE.jsonl", payload)
        safe = {
            "schema": SCHEMA,
            "status": "OWNER_EVIDENCE_TEMPLATE_CREATED__NOT_EVIDENCE",
            "staged_candidates": len(rows),
            "template_rows": len(rows),
            "owner_evidence_populated": False,
            "attestations_populated": 0,
            "private_template_file_sha256": digest,
            "private_values_emitted": False,
            "quality_v1_admitted": 0,
            "training_authorized": False,
            "gpu_started": False,
            "r50_accessed": False,
        }
        _create_only(
            output_dir / "OWNER_EVIDENCE_TEMPLATE_SAFE.json",
            json.dumps(safe, sort_keys=True, indent=2).encode() + b"\\n",
        )
    except BaseException:
        for item in output_dir.iterdir():
            item.unlink()
        output_dir.rmdir()
        raise
    return safe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged-jsonl", type=Path, required=True)
    parser.add_argument("--staging-safe", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run(args.staged_jsonl, args.staging_safe, args.output_dir)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - do not expose private paths, IDs, hashes or values
        print(json.dumps({
            "schema": SCHEMA,
            "status": "OWNER_EVIDENCE_TEMPLATE_HOLD",
            "owner_evidence_populated": False,
            "quality_v1_admitted": 0,
            "training_authorized": False,
            "gpu_started": False,
            "r50_accessed": False,
            "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
