"""Create an independently verified R60 v2 Owner package with 39 explicit approvals.

The tool is create-only. It preserves original inputs and semantic checks,
validates both AI advisory sets (35 NOT_SUPPORTED + 4 SUPPORTED), applies only
the Owner-approved history_complete assertions, normalizes evidence locators,
then runs the unchanged official v2 verifier. No GPU/HF/SFT/admission.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

PACKET = "OWNER_ADJUDICATION_BLIND_PACKETS_PRIVATE.jsonl"
RESULTS = "OWNER_ADJUDICATION_RESULTS_PRIVATE.jsonl"
SEMANTIC = "OWNER_SEMANTIC_ENTAILMENT_CHECKS_PRIVATE.jsonl"
SCHEMA = "OWNER_ADJUDICATION_SCHEMA_V2.json"
AI35 = "OWNER_HISTORY_COMPLETENESS_AI_REVIEW_35_PRIVATE.jsonl"
SAFE35 = "OWNER_HISTORY_COMPLETENESS_AI_REVIEW_35_SAFE.json"
WORKSHEET4 = "OWNER_SUPPORTED_HISTORY_COMPLETENESS_REVIEW_4_PRIVATE.jsonl"
AI4 = "OWNER_SUPPORTED_HISTORY_COMPLETENESS_AI_REVIEW_4_PRIVATE.jsonl"
SAFE4 = "OWNER_SUPPORTED_HISTORY_COMPLETENESS_AI_REVIEW_4_SAFE.json"
APPROVAL = "OWNER_HISTORY_COMPLETENESS_OWNER_APPROVAL_V2_PRIVATE.json"
PINNED = (PACKET, RESULTS, SEMANTIC, AI35, WORKSHEET4, AI4)
BASE_RECOMMENDATION = "CONFIRM_HISTORY_COMPLETE_AND_KEEP_NOT_SUPPORTED"
SUPPORTED_RECOMMENDATION = "CONFIRM_HISTORY_COMPLETE_AND_KEEP_SUPPORTED"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def stop(reason: str) -> None:
    print(json.dumps({
        "status": "OWNER_APPROVED_PACKAGE_V2_HOLD",
        "reason_code": reason,
        "originals_modified": False,
        "private_values_emitted": False,
        "gpu_started": False,
        "training_authorized": False,
    }, sort_keys=True))
    raise SystemExit(2)


def read_jsonl(raw: bytes, module, reason: str):
    return module._jsonl(raw, reason)


def private_file(path: Path, repo: Path, module) -> bytes:
    if not path.is_file() or path.is_symlink():
        stop("PRIVATE_INPUT_MISSING_OR_INVALID")
    info = path.lstat()
    if stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1:
        stop("PRIVATE_INPUT_PERMISSION_OR_LINK_HOLD")
    return module._read_private(path, repo)


def normalize_results(results, packets, approved_pairs, dimensions):
    """Deep-copy results and apply only exact (case, dimension) -> verdict approvals."""
    import copy

    packet_by_id = {row["calibration_id"]: row for row in packets}
    output = copy.deepcopy(results)
    confirmed = target_count = history_count = 0

    for result in output:
        case_ref = result["case_ref"]
        packet = packet_by_id.get(case_ref)
        if packet is None:
            stop("RESULT_PACKET_LINK_MISMATCH")
        for dimension in dimensions:
            assessment = result["assessments"][dimension]
            approved_verdict = approved_pairs.get((case_ref, dimension))
            if approved_verdict is not None:
                coverage = assessment["context_coverage"]
                if (assessment["verdict"] != approved_verdict
                        or coverage.get("history_complete") is not False
                        or coverage.get("target_complete") is not True
                        or coverage.get("relevant_context_complete") is not True
                        or assessment.get("missing_context") != []
                        or not assessment.get("evidence")):
                    stop("OWNER_APPROVAL_PRECONDITION_MISMATCH")
                coverage["history_complete"] = True
                confirmed += 1

            history = packet.get("visible_history", [])
            for evidence in assessment["evidence"]:
                source = evidence.get("source")
                if source == "target":
                    if evidence.get("message_index") != -1 or not evidence.get("component_ref"):
                        stop("UNEXPECTED_TARGET_LOCATOR_SHAPE")
                    evidence["message_index"] = 0
                    evidence["component_ref"] = ""
                    target_count += 1
                elif source == "history":
                    index = evidence.get("message_index")
                    if (type(index) is not int or not 0 <= index < len(history)
                            or not evidence.get("component_ref")):
                        stop("UNEXPECTED_HISTORY_LOCATOR_SHAPE")
                    evidence["component_ref"] = ""
                    history_count += 1
                else:
                    stop("UNEXPECTED_EVIDENCE_SOURCE")
    return output, {
        "history_completeness_confirmed": confirmed,
        "target_locators_normalized": target_count,
        "history_locators_normalized": history_count,
    }


def canonical_json(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def validate_safe35(safe: dict) -> None:
    if (safe.get("schema") != "storyforge_history_completeness_ai_review_safe_v1"
            or safe.get("covered_all_35") is not True
            or safe.get("total_reviews") != 35
            or safe.get("recommendation_counts") != {
                BASE_RECOMMENDATION: 35,
                "CHANGE_TO_INSUFFICIENT_CONTEXT": 0,
                "HOLD_UNRESOLVED": 0,
            }
            or safe.get("owner_final_decision_recorded") is not False
            or safe.get("reviewer_type") != "AI_ADVISORY_NOT_OWNER"):
        stop("AI35_SAFE_CONTRACT_HOLD")


def validate_safe4(safe: dict) -> None:
    if (safe.get("schema") != "storyforge_r60_supported_history_completeness_ai_review_safe_v1"
            or safe.get("total_reviews") != 4
            or safe.get("dimension_counts") != {"player_agency": 4}
            or safe.get("original_verdict_counts") != {"SUPPORTED": 4}
            or safe.get("recommendation_counts") != {
                SUPPORTED_RECOMMENDATION: 4,
                "CHANGE_TO_INSUFFICIENT_CONTEXT": 0,
                "HOLD_UNRESOLVED": 0,
            }
            or safe.get("covered_all_4") is not True
            or safe.get("original_case_order_preserved") is not True
            or safe.get("original_files_modified") is not False
            or safe.get("original_semantic_checks_modified") is not False
            or safe.get("private_values_emitted") is not False
            or safe.get("reviewer_type") != "AI_ADVISORY_NOT_OWNER"
            or safe.get("owner_final_decision_recorded") is not False):
        stop("AI4_SAFE_CONTRACT_HOLD")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-sha256-json", type=Path, required=True,
                        help="Private SHA-256 pin map for the six pinned inputs.")
    parser.add_argument("--owner-approved", action="store_true",
                        help="Explicitly attest that Owner approved both AI advisory sets (39 exact pairs).")
    args = parser.parse_args()
    if not args.owner_approved:
        stop("EXPLICIT_OWNER_APPROVAL_FLAG_REQUIRED")

    repo = args.repo_root.resolve(strict=True)
    source = args.source_dir.expanduser()
    output = args.output_dir.expanduser()
    pin_path = args.expected_sha256_json.expanduser()
    if not source.is_absolute() or not output.is_absolute() or not pin_path.is_absolute():
        stop("PRIVATE_PATH_MUST_BE_ABSOLUTE")
    if source.is_symlink() or not source.is_dir() or stat.S_IMODE(source.stat().st_mode) != 0o700:
        stop("SOURCE_DIRECTORY_MODE_OR_TYPE_HOLD")
    if output.exists() or output.is_symlink() or not output.parent.is_dir():
        stop("OUTPUT_MUST_BE_NEW_DIRECTORY")
    if stat.S_IMODE(output.parent.stat().st_mode) != 0o700:
        stop("PRIVATE_PARENT_MODE_NOT_0700")
    if pin_path.is_symlink() or not pin_path.is_file():
        stop("SHA_PIN_FILE_MISSING_OR_INVALID")
    if stat.S_IMODE(pin_path.stat().st_mode) != 0o600:
        stop("SHA_PIN_FILE_MODE_HOLD")
    if any(parent.is_symlink() for parent in (source, *source.parents, output, *output.parents)):
        stop("SYMLINK_PATH_COMPONENT_HOLD")
    if output.resolve(strict=False) == repo or repo in output.resolve(strict=False).parents:
        stop("OUTPUT_INSIDE_REPOSITORY")

    sys.path.insert(0, str(repo / "src"))
    from storyforge_gold_quality import hf_owner_adjudication_v2 as adjudication
    from storyforge_gold_quality import hf_severity_evidence_v2 as severity

    expected = json.loads(pin_path.read_text(encoding="utf-8"))
    if not isinstance(expected, dict) or set(expected) != set(PINNED):
        stop("EXPECTED_SHA_MANIFEST_SHAPE_HOLD")

    names = (*PINNED, SCHEMA, SAFE35, SAFE4)
    raw = {name: private_file(source / name, repo, adjudication) for name in names}
    for name in PINNED:
        if sha(raw[name]) != expected[name]:
            stop("INPUT_SHA256_MISMATCH")

    safe35 = json.loads(raw[SAFE35])
    safe4 = json.loads(raw[SAFE4])
    validate_safe35(safe35)
    validate_safe4(safe4)

    packets = read_jsonl(raw[PACKET], adjudication, "PACKET_JSONL_INVALID")
    results = read_jsonl(raw[RESULTS], adjudication, "RESULT_JSONL_INVALID")
    checks = read_jsonl(raw[SEMANTIC], adjudication, "SEMANTIC_JSONL_INVALID")
    advice35 = read_jsonl(raw[AI35], adjudication, "AI35_JSONL_INVALID")
    worksheet4 = read_jsonl(raw[WORKSHEET4], adjudication, "WORKSHEET4_JSONL_INVALID")
    advice4 = read_jsonl(raw[AI4], adjudication, "AI4_JSONL_INVALID")
    if (len(packets), len(results), len(checks), len(advice35), len(worksheet4), len(advice4)) != (20, 20, 60, 35, 4, 4):
        stop("SOURCE_CARDINALITY_HOLD")

    result_ids = {row.get("case_ref") for row in results}
    packet_ids = {row.get("calibration_id") for row in packets}
    if len(result_ids) != 20 or result_ids != packet_ids:
        stop("PACKET_RESULT_ID_SET_HOLD")

    result_by_id = {row["case_ref"]: row for row in results}
    semantic_by_pair = {}
    for row in checks:
        pair = (row.get("calibration_id"), row.get("dimension"))
        if pair in semantic_by_pair:
            stop("SEMANTIC_CHECK_DUPLICATE")
        semantic_by_pair[pair] = row
    if len(semantic_by_pair) != 60:
        stop("SEMANTIC_CHECK_COVERAGE_HOLD")

    approved_pairs = {}
    for row in advice35:
        pair = (row.get("calibration_id"), row.get("dimension"))
        if (row.get("reviewer_type") != "AI_ADVISORY_NOT_OWNER"
                or row.get("ai_recommendation") != BASE_RECOMMENDATION
                or row.get("semantic_recheck_required") is not False
                or pair in approved_pairs or pair[0] not in result_ids
                or pair[1] not in severity.DIMENSIONS):
            stop("AI35_ROW_CONTRACT_HOLD")
        approved_pairs[pair] = "NOT_SUPPORTED"

    expected35 = {
        (case_ref, dimension)
        for case_ref, result in result_by_id.items()
        for dimension in severity.DIMENSIONS
        if result["assessments"][dimension]["verdict"] == "NOT_SUPPORTED"
        and result["assessments"][dimension]["context_coverage"]["history_complete"] is False
    }
    if set(approved_pairs) != expected35 or len(approved_pairs) != 35:
        stop("AI35_PAIR_SET_MISMATCH")

    expected4 = []
    for row_number, result in enumerate(results, 1):
        assessment = result["assessments"]["player_agency"]
        coverage = assessment["context_coverage"]
        if assessment["verdict"] == "SUPPORTED" and coverage["history_complete"] is False:
            expected4.append((row_number, result["case_ref"], assessment))
    if [row[0] for row in expected4] != [5, 6, 11, 19]:
        stop("SUPPORTED_CASE_ORDER_OR_COUNT_MISMATCH")

    if [row.get("result_row") for row in worksheet4] != [5, 6, 11, 19]:
        stop("WORKSHEET_ORDER_MISMATCH")

    for (row_number, case_ref, assessment), worksheet_row, advisory in zip(
            expected4, worksheet4, advice4, strict=True):
        if (worksheet_row.get("calibration_id") != case_ref
                or worksheet_row.get("dimension") != "player_agency"
                or worksheet_row.get("current_verdict") != "SUPPORTED"
                or worksheet_row.get("current_assessment") != assessment
                or worksheet_row.get("current_semantic_check") != semantic_by_pair.get((case_ref, "player_agency"))):
            stop("WORKSHEET_SOURCE_BINDING_MISMATCH")
        owner_review = advisory.get("owner_review", {})
        reviewer_type = advisory.get("reviewer_type", owner_review.get("reviewer_type"))
        recommendation = advisory.get("ai_recommendation", owner_review.get("decision"))
        if (advisory.get("result_row") != row_number
                or advisory.get("calibration_id") != case_ref
                or advisory.get("dimension") != "player_agency"
                or reviewer_type != "AI_ADVISORY_NOT_OWNER"
                or recommendation != SUPPORTED_RECOMMENDATION
                or owner_review.get("history_completeness_confirmed") is not True
                or owner_review.get("revised_verdict_if_changed") not in ("", None)
                or owner_review.get("missing_context_if_changed") not in ([], None)
                or advisory.get("semantic_recheck_required", False) is not False):
            stop("AI4_ROW_CONTRACT_HOLD")
        if (owner_review.get("decision") not in (SUPPORTED_RECOMMENDATION, "")
                and recommendation != SUPPORTED_RECOMMENDATION):
            stop("AI4_DECISION_FIELD_MISMATCH")
        approved_pairs[(case_ref, "player_agency")] = "SUPPORTED"

    if len(approved_pairs) != 39 or set(approved_pairs) != expected35 | {
        (row[1], "player_agency") for row in expected4
    }:
        stop("TOTAL_APPROVED_PAIR_SET_MISMATCH")

    normalized, counts = normalize_results(
        results, packets, approved_pairs, severity.DIMENSIONS
    )
    if counts != {
        "history_completeness_confirmed": 39,
        "target_locators_normalized": 60,
        "history_locators_normalized": 20,
    }:
        stop("NORMALIZATION_COUNT_HOLD")

    normalized_raw = b"".join(adjudication.canonical(row) + b"\n" for row in normalized)
    manifest, pure_safe = adjudication.verify_owner_results(raw[PACKET], normalized_raw, raw[SEMANTIC])
    if (manifest.get("case_count") != 20 or manifest.get("semantic_check_count") != 60
            or pure_safe.get("status") != "OWNER_REVIEW_COMPLETE__SEMANTIC_HOLDS_PRESERVED"):
        stop("PURE_VERIFIER_POSTCONDITION_HOLD")

    approval = {
        "schema": "storyforge_r60_owner_history_completeness_owner_approval_v2",
        "status": "OWNER_APPROVED_ALL_39_AI_RECOMMENDATIONS",
        "approved_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "approved_recommendation_count": 39,
        "approved_dimensions": {"player_agency": 20, "safety": 19, "hard_rule": 0},
        "approved_original_verdicts": {"NOT_SUPPORTED": 35, "SUPPORTED": 4},
        "decision": {
            "history_complete": True,
            "verdict_changes": 0,
            "semantic_rechecks_required": 0,
        },
        "ai_advisory_sha256": {AI35: sha(raw[AI35]), AI4: sha(raw[AI4])},
        "source_sha256": {name: sha(raw[name]) for name in PINNED},
        "originals_modified": False,
        "semantic_checks_modified": False,
        "gpu_started": False,
        "training_authorized": False,
        "private_values_emitted": False,
    }
    outputs = {
        PACKET: raw[PACKET],
        RESULTS: normalized_raw,
        SEMANTIC: raw[SEMANTIC],
        SCHEMA: raw[SCHEMA],
        AI35: raw[AI35],
        SAFE35: raw[SAFE35],
        WORKSHEET4: raw[WORKSHEET4],
        AI4: raw[AI4],
        SAFE4: raw[SAFE4],
        APPROVAL: adjudication.canonical(approval) + b"\n",
    }
    output.mkdir(mode=0o700)
    output.chmod(0o700)
    created = []
    try:
        for filename, content in outputs.items():
            target = output / filename
            adjudication._write_once(target, content)
            created.append(target)
        for path in created:
            info = path.lstat()
            if (not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode)
                    or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1):
                raise adjudication.AdjudicationHold("OUTPUT_PERMISSION_POSTCHECK_HOLD")
    except BaseException:
        for path in reversed(created):
            path.unlink(missing_ok=True)
        try:
            output.rmdir()
        except OSError:
            pass
        raise

    env = dict(os.environ)
    env["PYTHONPATH"] = str(repo / "src")
    proc = subprocess.run(
        [sys.executable, str(repo / "scripts/r60_owner_adjudication_verify_v2.py"),
         "--repo-root", str(repo), "--package-dir", str(output)],
        check=False, cwd=repo, env=env, text=True, capture_output=True,
    )
    try:
        safe = json.loads(proc.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        safe = {}
    if proc.returncode != 0:
        print(json.dumps({
            "status": "PACKAGE_CREATED_OFFICIAL_VERIFIER_HOLD",
            "reason_code": safe.get("reason_code", "UNPARSEABLE_SAFE"),
            "output_dir": str(output),
            **counts,
            "originals_modified": False,
            "private_values_emitted": False,
            "gpu_started": False,
            "training_authorized": False,
        }, sort_keys=True))
        return 42

    manifest_path = output / "OWNER_ADJUDICATION_RESULTS_MANIFEST_PRIVATE.json"
    safe_path = output / "OWNER_ADJUDICATION_RESULTS_SAFE.json"
    print(json.dumps({
        "status": safe.get("status"),
        "output_dir": str(output),
        **counts,
        "cases_verified": safe.get("cases_verified"),
        "semantic_checks_verified": safe.get("semantic_checks_verified"),
        "semantic_supported_count": safe.get("semantic_supported_count"),
        "semantic_insufficient_context_count": safe.get("semantic_insufficient_context_count"),
        "semantic_not_established_count": safe.get("semantic_not_established_count"),
        "input_sha256": {name: sha(raw[name]) for name in PINNED},
        "output_sha256": {name: sha((output / name).read_bytes()) for name in outputs},
        "approval_sha256": sha((output / APPROVAL).read_bytes()),
        "manifest_sha256": sha(manifest_path.read_bytes()),
        "safe_sha256": sha(safe_path.read_bytes()),
        "originals_modified": False,
        "semantic_checks_modified": False,
        "private_values_emitted": False,
        "quality_v1_admitted": safe.get("quality_v1_admitted"),
        "training_authorized": safe.get("training_authorized"),
        "gpu_started": safe.get("gpu_started"),
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
