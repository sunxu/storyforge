"""Strictly migrate legacy R60 evidence locators into the official v2 locator contract.

Only locator fields change:
  target: (-1, "target_text") -> (0, "")
  history: (valid index, "visible_history") -> (same index, "")
All quotes, offsets, roles, verdicts, reasoning and other fields are preserved.
A new private package is written; source files are never modified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from pathlib import Path

from storyforge_gold_quality import hf_owner_adjudication_v2 as adjudication
from storyforge_gold_quality import hf_severity_evidence_v2 as severity

PACKET = adjudication.PACKET_NAME
RESULT = "OWNER_ADJUDICATION_RESULTS_PRIVATE.jsonl"
CHECKS = "OWNER_SEMANTIC_ENTAILMENT_CHECKS_PRIVATE.jsonl"


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_private(path: Path, repo_root: Path):
    value = adjudication._read_private(path, repo_root)
    if not isinstance(value, list) or not value or any(not isinstance(x, dict) for x in value):
        raise adjudication.AdjudicationHold("MIGRATION_JSONL_SHAPE_HOLD")
    return value, path.read_bytes()


def write_once(path: Path, raw: bytes) -> None:
    adjudication._write_once(path, raw)


def jsonl(rows: list[dict]) -> bytes:
    return b"".join(adjudication.canonical(row) + b"\\n" for row in rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--source-package-dir", type=Path, required=True)
    ap.add_argument("--output-package-dir", type=Path, required=True)
    args = ap.parse_args()
    out = None
    try:
        root = args.repo_root.resolve(strict=True)
        src, out = args.source_package_dir.expanduser(), args.output_package_dir.expanduser()
        for label, p in (("SOURCE", src), ("OUTPUT", out)):
            if not p.is_absolute() or p.is_symlink() or any(x.is_symlink() for x in p.parents):
                raise adjudication.AdjudicationHold(f"MIGRATION_{label}_PATH_HOLD")
            resolved = p.resolve(strict=(label == "SOURCE"))
            if resolved == root or root in resolved.parents:
                raise adjudication.AdjudicationHold(f"MIGRATION_{label}_INSIDE_REPO_HOLD")
        if not src.is_dir() or stat.S_IMODE(src.stat().st_mode) != 0o700:
            raise adjudication.AdjudicationHold("MIGRATION_SOURCE_DIRECTORY_MODE_HOLD")
        if out.exists() or src.resolve() == out.resolve():
            raise adjudication.AdjudicationHold("MIGRATION_OUTPUT_EXISTS_OR_COLLISION_HOLD")

        packets, packet_raw = read_private(src / PACKET, root)
        results, result_raw = read_private(src / RESULT, root)
        checks, checks_raw = read_private(src / CHECKS, root)
        if (len(packets), len(results), len(checks)) != (20, 20, 60):
            raise adjudication.AdjudicationHold("MIGRATION_INPUT_CARDINALITY_HOLD")
        packet_map = {p.get("calibration_id"): p for p in packets}
        if len(packet_map) != 20 or len({r.get("case_ref") for r in results}) != 20:
            raise adjudication.AdjudicationHold("MIGRATION_CASE_LINKAGE_HOLD")
        if set(packet_map) != {r.get("case_ref") for r in results}:
            raise adjudication.AdjudicationHold("MIGRATION_CASE_LINKAGE_HOLD")

        migrated = json.loads(json.dumps(results, ensure_ascii=False))
        targets = histories = 0
        for result in migrated:
            packet = packet_map[result["case_ref"]]
            assessments = result.get("assessments")
            if not isinstance(assessments, dict) or set(assessments) != set(severity.DIMENSIONS):
                raise adjudication.AdjudicationHold("MIGRATION_DIMENSION_SET_HOLD")
            for dimension in severity.DIMENSIONS:
                evidence = assessments[dimension].get("evidence")
                if not isinstance(evidence, list):
                    raise adjudication.AdjudicationHold("MIGRATION_EVIDENCE_LIST_HOLD")
                for item in evidence:
                    if not isinstance(item, dict):
                        raise adjudication.AdjudicationHold("MIGRATION_EVIDENCE_ITEM_HOLD")
                    source = item.get("source")
                    if source == "target":
                        if (item.get("message_index"), item.get("component_ref")) != (-1, "target_text"):
                            raise adjudication.AdjudicationHold("MIGRATION_TARGET_LEGACY_LOCATOR_MISMATCH")
                        item["message_index"], item["component_ref"] = 0, ""
                        targets += 1
                    elif source == "history":
                        idx = item.get("message_index")
                        history = packet.get("visible_history")
                        if (type(idx) is not int or not isinstance(history, list)
                                or not 0 <= idx < len(history)
                                or item.get("component_ref") != "visible_history"):
                            raise adjudication.AdjudicationHold("MIGRATION_HISTORY_LEGACY_LOCATOR_MISMATCH")
                        item["component_ref"] = ""
                        histories += 1
                    elif source == "verified_world_component":
                        if item.get("message_index") != -1 or not item.get("component_ref"):
                            raise adjudication.AdjudicationHold("MIGRATION_COMPONENT_LOCATOR_HOLD")
                    else:
                        raise adjudication.AdjudicationHold("MIGRATION_UNKNOWN_SOURCE_HOLD")
                # Official code checks source/role rules, exact quote, offsets and duplicates.
                severity._validate_evidence(packet, evidence)

        if (targets, histories) != (60, 20):
            raise adjudication.AdjudicationHold("MIGRATION_EXPECTED_60_TARGET_20_HISTORY_HOLD")

        # Prove no non-locator evidence fields changed.
        old_map = {r["case_ref"]: r for r in results}
        for new in migrated:
            old = old_map[new["case_ref"]]
            for dim in severity.DIMENSIONS:
                for a, b in zip(old["assessments"][dim]["evidence"], new["assessments"][dim]["evidence"]):
                    if any(a.get(k) != b.get(k) for k in (set(a) | set(b)) - {"message_index", "component_ref"}):
                        raise adjudication.AdjudicationHold("MIGRATION_NON_LOCATOR_FIELD_CHANGED_HOLD")

        out.mkdir(mode=0o700, parents=False, exist_ok=False)
        os.chmod(out, 0o700)
        try:
            write_once(out / PACKET, packet_raw)
            write_once(out / RESULT, jsonl(migrated))
            write_once(out / CHECKS, checks_raw)
            safe = {
                "schema": "storyforge_r60_owner_evidence_locator_migration_safe_v1",
                "status": "MIGRATION_PASS__OFFICIAL_VERIFIER_PENDING",
                "cases": 20, "semantic_check_rows_copied": 60,
                "target_locators_migrated": targets,
                "history_locators_migrated": histories,
                "total_locators_migrated": targets + histories,
                "official_exact_quote_offset_role_validation": "PASS",
                "non_locator_evidence_fields_changed": 0,
                "original_files_modified": False,
                "gpu_started": False, "hf_jobs_submitted": 0,
                "training_authorized": False,
                "source_sha256": {
                    PACKET: digest(packet_raw), RESULT: digest(result_raw), CHECKS: digest(checks_raw)
                },
                "migrated_results_sha256": digest((out / RESULT).read_bytes()),
            }
            write_once(out / "EVIDENCE_LOCATOR_MIGRATION_SAFE.json",
                       adjudication.canonical(safe) + b"\\n")
            manifest = {
                "schema": "storyforge_r60_owner_evidence_locator_migration_manifest_v1",
                "files": {p.name: {"bytes": p.stat().st_size, "sha256": digest(p.read_bytes())}
                          for p in sorted(out.iterdir()) if p.is_file()}
            }
            write_once(out / "MANIFEST_PRIVATE.json", adjudication.canonical(manifest) + b"\\n")
        except BaseException:
            for p in out.iterdir():
                if p.is_file() and not p.is_symlink():
                    p.unlink()
            out.rmdir()
            raise
        print(json.dumps(safe, sort_keys=True))
        return 0
    except (adjudication.AdjudicationHold, OSError, ValueError, TypeError, KeyError) as exc:
        reason = str(exc) if isinstance(exc, adjudication.AdjudicationHold) else "MIGRATION_INPUT_OR_IO_ERROR"
        print(json.dumps({
            "schema": "storyforge_r60_owner_evidence_locator_migration_safe_v1",
            "status": "MIGRATION_HOLD", "reason_code": reason,
            "original_files_modified": False, "private_values_emitted": False,
            "gpu_started": False, "training_authorized": False
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
