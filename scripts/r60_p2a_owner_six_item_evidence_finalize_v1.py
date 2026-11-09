"""Apply the six explicitly approved R60 Owner evidence updates to a v2 normalized private package.

This is a create-only post-normalizer step. It preserves the source package, adds
only the six exact evidence rows approved for items 5, 34, 51 and 58, updates
the corresponding reviewed evidence indexes, and reruns the unchanged official
Owner verifier. Items 10 and 55 retain their approved decisions without adding
duplicate/overlapping evidence.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

from storyforge_gold_quality import hf_owner_adjudication_v2 as adjudication
from storyforge_gold_quality import hf_severity_evidence_v2 as severity

REVIEWER_REF = "owner-independent-r60-p2a-dev20-20261109"
UPDATE_SCHEMA = "storyforge_r60_owner_conversation_decision_update_v1"
UPDATE_STATUS = "OWNER_LATEST_CONVERSATION_DECISIONS_CAPTURED__NOT_FORMAL_RECEIPT"
EXPECTED_ITEMS = {5, 10, 34, 51, 55, 58}
ADD_EVIDENCE_COUNTS = {5: 1, 34: 3, 51: 1, 58: 1}
OFFICIAL_OUTPUTS = {
    "OWNER_ADJUDICATION_RESULTS_MANIFEST_PRIVATE.json",
    "OWNER_ADJUDICATION_RESULTS_SAFE.json",
    "MANIFEST_PRIVATE.json",
}
RESULTS = "OWNER_ADJUDICATION_RESULTS_PRIVATE.jsonl"
CHECKS = "OWNER_SEMANTIC_ENTAILMENT_CHECKS_PRIVATE.jsonl"
PACKETS = adjudication.PACKET_NAME


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _load_jsonl(raw: bytes, reason: str) -> list[dict]:
    return adjudication._jsonl(raw, reason)


def _normalize_locator(packet: dict, candidate: dict) -> dict:
    row = copy.deepcopy(candidate)
    source = row.get("source")
    if source == "target":
        if (row.get("message_index"), row.get("component_ref")) != (-1, "target_text"):
            raise adjudication.AdjudicationHold("SIX_ITEM_TARGET_LOCATOR_SHAPE_HOLD")
        row["message_index"] = 0
        row["component_ref"] = ""
    elif source == "history":
        index = row.get("message_index")
        history = packet.get("visible_history")
        if (type(index) is not int or not isinstance(history, list)
                or not 0 <= index < len(history)
                or row.get("component_ref") != "visible_history"):
            raise adjudication.AdjudicationHold("SIX_ITEM_HISTORY_LOCATOR_SHAPE_HOLD")
        row["component_ref"] = ""
    else:
        raise adjudication.AdjudicationHold("SIX_ITEM_UNKNOWN_EVIDENCE_SOURCE_HOLD")
    return row


def apply_owner_updates(packets: list[dict], results: list[dict],
                        checks: list[dict], update: dict) -> tuple[list, list, dict]:
    """Pure transformation; original inputs remain unchanged."""
    if (update.get("schema") != UPDATE_SCHEMA
            or update.get("status") != UPDATE_STATUS):
        raise adjudication.AdjudicationHold("SIX_ITEM_UPDATE_SCHEMA_HOLD")
    latest = update.get("latest_six_decisions")
    if not isinstance(latest, list) or {x.get("item") for x in latest} != EXPECTED_ITEMS:
        raise adjudication.AdjudicationHold("SIX_ITEM_UPDATE_COVERAGE_HOLD")

    packet_by_id = {x.get("calibration_id"): x for x in packets}
    result_by_id = {x.get("case_ref"): x for x in copy.deepcopy(results)}
    check_by_pair = {
        (x.get("calibration_id"), x.get("dimension")): x
        for x in copy.deepcopy(checks)
    }
    if len(packet_by_id) != 20 or len(result_by_id) != 20 or len(check_by_pair) != 60:
        raise adjudication.AdjudicationHold("SIX_ITEM_SOURCE_CARDINALITY_HOLD")
    if set(packet_by_id) != set(result_by_id):
        raise adjudication.AdjudicationHold("SIX_ITEM_PACKET_RESULT_LINK_HOLD")

    # All existing rows must already be true Owner-confirmed checks, not AI advisory rows.
    for pair, row in check_by_pair.items():
        check = row.get("check", {})
        if (set(row) != {"calibration_id", "dimension", "reviewed_at_utc", "check"}
                or check.get("reviewer_role") != "OWNER_INDEPENDENT"
                or check.get("reviewer_ref") != REVIEWER_REF
                or check.get("rubric_version") != severity.RUBRIC_VERSION):
            raise adjudication.AdjudicationHold("SIX_ITEM_OWNER_CHECK_BINDING_HOLD")

    additions = 0
    target_additions = 0
    history_additions = 0
    item_summaries = []
    for row in sorted(latest, key=lambda x: x["item"]):
        item = row["item"]
        case_ref = row.get("calibration_id")
        dimension = row.get("dimension")
        if case_ref not in result_by_id or dimension not in severity.DIMENSIONS:
            raise adjudication.AdjudicationHold("SIX_ITEM_CASE_DIMENSION_LINK_HOLD")
        packet = packet_by_id[case_ref]
        result = result_by_id[case_ref]
        assessment = result["assessments"][dimension]
        decision = row.get("owner_latest_conversation_decision", {})
        owner_reason = decision.get("reason")
        if not isinstance(owner_reason, str) or len(owner_reason.strip()) < 12:
            raise adjudication.AdjudicationHold("SIX_ITEM_OWNER_REASON_MISSING_HOLD")

        expected_verdict = {
            5: "INSUFFICIENT_CONTEXT",
            10: "NOT_SUPPORTED",
            34: "NOT_SUPPORTED",
            51: "INSUFFICIENT_CONTEXT",
            55: "SUPPORTED",
            58: "SUPPORTED",
        }[item]
        if assessment.get("verdict") != expected_verdict or decision.get("verdict") != expected_verdict:
            raise adjudication.AdjudicationHold("SIX_ITEM_VERDICT_BINDING_HOLD")

        evidence = assessment.get("evidence")
        if not isinstance(evidence, list):
            raise adjudication.AdjudicationHold("SIX_ITEM_EVIDENCE_LIST_HOLD")
        before = len(evidence)
        candidates = row.get("evidence_supplement_candidates", [])
        expected_add = ADD_EVIDENCE_COUNTS.get(item, 0)
        if len(candidates) != {5: 1, 10: 2, 34: 3, 51: 1, 55: 3, 58: 3}[item]:
            raise adjudication.AdjudicationHold("SIX_ITEM_CANDIDATE_COUNT_HOLD")

        # Add only the Owner-approved, non-duplicate evidence candidates.
        selected = {
            5: [0],
            34: [0, 1, 2],
            51: [0],
            58: [2],
        }.get(item, [])
        for candidate_index in selected:
            candidate = _normalize_locator(packet, candidates[candidate_index])
            severity._validate_evidence(packet, [candidate])
            identity = (
                candidate.get("source"), candidate.get("message_index"),
                candidate.get("start_char"), candidate.get("end_char"),
                candidate.get("quote"), candidate.get("role"),
            )
            existing = {
                (e.get("source"), e.get("message_index"), e.get("start_char"),
                 e.get("end_char"), e.get("quote"), e.get("role"))
                for e in evidence
            }
            if identity in existing:
                raise adjudication.AdjudicationHold("SIX_ITEM_EXPECTED_NEW_EVIDENCE_ALREADY_PRESENT")
            evidence.append(candidate)
            additions += 1
            if candidate["source"] == "target":
                target_additions += 1
            else:
                history_additions += 1

        if len(evidence) - before != expected_add:
            raise adjudication.AdjudicationHold("SIX_ITEM_EVIDENCE_ADDITION_COUNT_HOLD")
        severity._validate_evidence(packet, evidence)

        check = check_by_pair[(case_ref, dimension)]["check"]
        check["reasoning_summary"] = owner_reason[:1200]
        check["reviewed_evidence_indexes"] = list(range(len(evidence)))
        if item == 5:
            check["conclusion"] = "INSUFFICIENT_CONTEXT"
        else:
            check["conclusion"] = "SUPPORTS_VERDICT"
        item_summaries.append({
            "item": item,
            "dimension": dimension,
            "evidence_added": len(evidence) - before,
            "latest_owner_decision_applied": True,
        })

    # Ensure all 60 check rows cover every evidence entry in the transformed Results.
    for (case_ref, dimension), row in check_by_pair.items():
        evidence = result_by_id[case_ref]["assessments"][dimension]["evidence"]
        indexes = row["check"].get("reviewed_evidence_indexes")
        if indexes != list(range(len(evidence))):
            raise adjudication.AdjudicationHold("SIX_ITEM_FINAL_EVIDENCE_INDEX_COVERAGE_HOLD")

    counts = {
        "items_updated": len(item_summaries),
        "evidence_added": additions,
        "target_evidence_added": target_additions,
        "history_evidence_added": history_additions,
        "item_summaries": item_summaries,
        "initial_decision_counts_preserved": {"A": 58, "B": 1, "C": 1},
        "item_10_latest_verdict": "NOT_SUPPORTED",
        "item_5_status": "INSUFFICIENT_CONTEXT_HOLD",
    }
    return list(result_by_id.values()), list(check_by_pair.values()), counts


def _private(path: Path, repo: Path) -> bytes:
    return adjudication._read_private(path, repo)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--source-package-dir", type=Path, required=True,
                        help="Successful output from owner_approved_package_normalizer_v2.py")
    parser.add_argument("--six-item-update-json", type=Path, required=True)
    parser.add_argument("--output-package-dir", type=Path, required=True)
    args = parser.parse_args()

    repo = args.repo_root.resolve(strict=True)
    source = args.source_package_dir.expanduser()
    update_path = args.six_item_update_json.expanduser()
    output = args.output_package_dir.expanduser()
    try:
        for label, path in (("SOURCE", source), ("UPDATE", update_path)):
            if not path.is_absolute() or path.is_symlink():
                raise adjudication.AdjudicationHold(f"SIX_ITEM_{label}_PATH_HOLD")
        if (not source.is_dir() or stat.S_IMODE(source.stat().st_mode) != 0o700
                or output.exists() or output.is_symlink()
                or not output.is_absolute() or not output.parent.is_dir()
                or stat.S_IMODE(output.parent.stat().st_mode) != 0o700
                or any(p.is_symlink() for p in (source, *source.parents, output, *output.parents))):
            raise adjudication.AdjudicationHold("SIX_ITEM_PRIVATE_DIRECTORY_HOLD")
        if output.resolve(strict=False) == repo or repo in output.resolve(strict=False).parents:
            raise adjudication.AdjudicationHold("SIX_ITEM_OUTPUT_INSIDE_REPOSITORY_HOLD")

        safe_raw = _private(source / "OWNER_ADJUDICATION_RESULTS_SAFE.json", repo)
        source_safe = adjudication._json(safe_raw, "SOURCE_OFFICIAL_SAFE_INVALID")
        if (source_safe.get("status") != "OWNER_REVIEW_COMPLETE__SEMANTIC_HOLDS_PRESERVED"
                or source_safe.get("cases_verified") != 20
                or source_safe.get("semantic_checks_verified") != 60
                or source_safe.get("gpu_started") is not False
                or source_safe.get("training_authorized") is not False):
            raise adjudication.AdjudicationHold("SOURCE_OFFICIAL_VERIFIER_NOT_PASS")

        packet_raw = _private(source / PACKETS, repo)
        result_raw = _private(source / RESULTS, repo)
        checks_raw = _private(source / CHECKS, repo)
        update_raw = _private(update_path, repo)
        packets = adjudication._jsonl(packet_raw, "PACKET_JSONL_INVALID")
        results = adjudication._jsonl(result_raw, "RESULT_JSONL_INVALID")
        checks = adjudication._jsonl(checks_raw, "SEMANTIC_CHECK_JSONL_INVALID")
        update = adjudication._json(update_raw, "SIX_ITEM_UPDATE_JSON_INVALID")
        derived_results, derived_checks, counts = apply_owner_updates(
            packets, results, checks, update
        )

        output.mkdir(mode=0o700, parents=False, exist_ok=False)
        output.chmod(0o700)
        try:
            # Copy the successful normalizer package except old official outputs/manifests.
            for path in sorted(source.iterdir()):
                if not path.is_file() or path.is_symlink() or path.name in OFFICIAL_OUTPUTS:
                    continue
                info = path.lstat()
                if stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1:
                    raise adjudication.AdjudicationHold("SOURCE_PACKAGE_FILE_MODE_HOLD")
                adjudication._write_once(output / path.name, path.read_bytes())
            adjudication._write_once(output / PACKETS, packet_raw)
            adjudication._write_once(
                output / RESULTS,
                b"".join(adjudication.canonical(x) + b"\n" for x in derived_results)
            )
            adjudication._write_once(
                output / CHECKS,
                b"".join(adjudication.canonical(x) + b"\n" for x in derived_checks)
            )
            adjudication._write_once(output / "OWNER_DECISION_UPDATE_SIX_ITEMS_PRIVATE.json", update_raw)
            safe = {
                "schema": "storyforge_r60_p2a_owner_six_item_evidence_finalize_safe_v1",
                "status": "SIX_ITEM_EVIDENCE_APPLIED__OFFICIAL_VERIFIER_PENDING",
                **{k: v for k, v in counts.items() if k != "item_summaries"},
                "item_summaries": counts["item_summaries"],
                "original_files_modified": False,
                "gpu_started": False, "hf_jobs_submitted": 0,
                "quality_v1_admitted": 0, "training_authorized": False,
            }
            adjudication._write_once(output / "OWNER_SIX_ITEM_EVIDENCE_FINALIZE_SAFE.json",
                                     adjudication.canonical(safe) + b"\n")

            verifier = repo / "scripts" / "r60_owner_adjudication_verify_v2.py"
            proc = subprocess.run(
                [sys.executable, str(verifier), "--repo-root", str(repo),
                 "--package-dir", str(output)],
                cwd=repo, capture_output=True, text=True, check=False,
            )
            try:
                verifier_safe = json.loads(proc.stdout.strip().splitlines()[-1])
            except (ValueError, IndexError):
                verifier_safe = {}
            if (proc.returncode != 0
                    or verifier_safe.get("status") != "OWNER_REVIEW_COMPLETE__SEMANTIC_HOLDS_PRESERVED"):
                reason = verifier_safe.get("reason_code", "OFFICIAL_VERIFIER_FAILED")
                raise adjudication.AdjudicationHold(f"SIX_ITEM_OFFICIAL_VERIFIER_{reason}")

            manifest = {
                "schema": "storyforge_r60_p2a_six_item_evidence_finalize_manifest_private_v1",
                "files": {
                    p.name: {"bytes": p.stat().st_size, "sha256": sha(p.read_bytes())}
                    for p in sorted(output.iterdir())
                    if p.is_file() and p.name != "MANIFEST_PRIVATE.json"
                },
            }
            adjudication._write_once(output / "MANIFEST_PRIVATE.json",
                                     adjudication.canonical(manifest) + b"\n")
            print(json.dumps({
                "schema": safe["schema"],
                "status": "SIX_ITEM_EVIDENCE_FINALIZE_AND_OFFICIAL_VERIFIER_PASS",
                "cases_verified": verifier_safe.get("cases_verified"),
                "semantic_checks_verified": verifier_safe.get("semantic_checks_verified"),
                "evidence_added": additions,
                "target_evidence_added": target_additions,
                "history_evidence_added": history_additions,
                "semantic_supported_count": verifier_safe.get("semantic_supported_count"),
                "semantic_insufficient_context_count": verifier_safe.get("semantic_insufficient_context_count"),
                "semantic_not_established_count": verifier_safe.get("semantic_not_established_count"),
                "gpu_started": False, "hf_jobs_submitted": 0,
                "quality_v1_admitted": 0, "training_authorized": False,
            }, sort_keys=True))
            return 0
        except BaseException:
            for p in output.iterdir():
                if p.is_file() and not p.is_symlink():
                    p.unlink()
            output.rmdir()
            raise
    except (adjudication.AdjudicationHold, OSError, ValueError, TypeError, KeyError) as exc:
        reason = str(exc) if isinstance(exc, adjudication.AdjudicationHold) else "SIX_ITEM_INPUT_OR_IO_ERROR"
        print(json.dumps({
            "schema": "storyforge_r60_p2a_owner_six_item_evidence_finalize_safe_v1",
            "status": "SIX_ITEM_EVIDENCE_FINALIZE_HOLD",
            "reason_code": reason,
            "private_values_emitted": False,
            "original_files_modified": False,
            "gpu_started": False, "training_authorized": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
