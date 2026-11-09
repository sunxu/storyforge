"""Create an independently verified R60 v2 Owner package after explicit approval.

This is a reusable, create-only utility for the fixed 20-result / 60-semantic-check
R60 Owner v2 contract. It never edits the source package. It requires an explicit
--owner-approved switch and verifies every AI advisory row before applying the
approved history-completeness assertion. No GPU, HF job, SFT, or admission action.
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
AI_REVIEW = "OWNER_HISTORY_COMPLETENESS_AI_REVIEW_35_PRIVATE.jsonl"
AI_SAFE = "OWNER_HISTORY_COMPLETENESS_AI_REVIEW_35_SAFE.json"
APPROVAL = "OWNER_HISTORY_COMPLETENESS_OWNER_APPROVAL_PRIVATE.json"
REQUIRED_SHA_FILES = (PACKET, RESULTS, SEMANTIC, AI_REVIEW)
RECOMMENDATION = "CONFIRM_HISTORY_COMPLETE_AND_KEEP_NOT_SUPPORTED"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def stop(reason: str) -> None:
    print(json.dumps({
        "status": "OWNER_APPROVED_PACKAGE_HOLD",
        "reason_code": reason,
        "originals_modified": False,
        "private_values_emitted": False,
        "gpu_started": False,
        "training_authorized": False,
    }, sort_keys=True))
    raise SystemExit(2)


def read_jsonl(raw: bytes, module, reason: str):
    return module._jsonl(raw, reason)


def write_once(path: Path, raw: bytes) -> None:
    fd = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        stat.S_IRUSR | stat.S_IWUSR,
    )
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o600)


def private_file(path: Path, repo_root: Path, module) -> bytes:
    if not path.is_file() or path.is_symlink():
        stop("PRIVATE_INPUT_MISSING_OR_INVALID")
    return module._read_private(path, repo_root)


def normalize_results(results, packets, approved_pairs, dimensions):
    """Return deep-copied results and aggregate locator/approval counts."""
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
            if (case_ref, dimension) in approved_pairs:
                coverage = assessment["context_coverage"]
                if (assessment["verdict"] != "NOT_SUPPORTED"
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-sha256-json", type=Path, required=True,
                        help="Private JSON mapping the four pinned input filenames to SHA-256.")
    parser.add_argument("--owner-approved", action="store_true",
                        help="Explicitly attest that the Owner approved all unanimous AI recommendations.")
    args = parser.parse_args()

    if not args.owner_approved:
        stop("EXPLICIT_OWNER_APPROVAL_FLAG_REQUIRED")

    repo = args.repo_root.resolve(strict=True)
    source = args.source_dir.expanduser()
    output = args.output_dir.expanduser()
    if not source.is_absolute() or not output.is_absolute():
        stop("PRIVATE_PATH_MUST_BE_ABSOLUTE")
    if source.is_symlink() or not source.is_dir() or stat.S_IMODE(source.stat().st_mode) != 0o700:
        stop("SOURCE_DIRECTORY_MODE_OR_TYPE_HOLD")
    if output.exists() or output.is_symlink() or not output.parent.is_dir():
        stop("OUTPUT_MUST_BE_NEW_DIRECTORY")
    if stat.S_IMODE(output.parent.stat().st_mode) != 0o700:
        stop("PRIVATE_PARENT_MODE_NOT_0700")
    if any(parent.is_symlink() for parent in (source, *source.parents, output, *output.parents)):
        stop("SYMLINK_PATH_COMPONENT_HOLD")
    if output.resolve(strict=False) == repo or repo in output.resolve(strict=False).parents:
        stop("OUTPUT_INSIDE_REPOSITORY")

    sys.path.insert(0, str(repo / "src"))
    from storyforge_gold_quality import hf_owner_adjudication_v2 as adjudication
    from storyforge_gold_quality import hf_severity_evidence_v2 as severity

    expected = json.loads(args.expected_sha256_json.read_text(encoding="utf-8"))
    if not isinstance(expected, dict) or set(expected) != set(REQUIRED_SHA_FILES):
        stop("EXPECTED_SHA_MANIFEST_SHAPE_HOLD")

    names = (*REQUIRED_SHA_FILES, SCHEMA, AI_SAFE)
    raw = {name: private_file(source / name, repo, adjudication) for name in names}
    for name in REQUIRED_SHA_FILES:
        if sha(raw[name]) != expected[name]:
            stop("INPUT_SHA256_MISMATCH")

    ai_safe = json.loads(raw[AI_SAFE])
    if (ai_safe.get("schema") != "storyforge_history_completeness_ai_review_safe_v1"
            or ai_safe.get("covered_all_35") is not True
            or ai_safe.get("total_reviews") != 35
            or ai_safe.get("recommendation_counts") != {
                RECOMMENDATION: 35,
                "CHANGE_TO_INSUFFICIENT_CONTEXT": 0,
                "HOLD_UNRESOLVED": 0,
            }
            or ai_safe.get("owner_final_decision_recorded") is not False
            or ai_safe.get("reviewer_type") != "AI_ADVISORY_NOT_OWNER"):
        stop("AI_ADVISORY_SAFE_CONTRACT_HOLD")

    packets = read_jsonl(raw[PACKET], adjudication, "PACKET_JSONL_INVALID")
    results = read_jsonl(raw[RESULTS], adjudication, "RESULT_JSONL_INVALID")
    checks = read_jsonl(raw[SEMANTIC], adjudication, "SEMANTIC_JSONL_INVALID")
    advice = read_jsonl(raw[AI_REVIEW], adjudication, "AI_REVIEW_JSONL_INVALID")
    if (len(packets), len(results), len(checks), len(advice)) != (20, 20, 60, 35):
        stop("SOURCE_CARDINALITY_HOLD")

    result_ids = {row.get("case_ref") for row in results}
    packet_ids = {row.get("calibration_id") for row in packets}
    if len(result_ids) != 20 or result_ids != packet_ids:
        stop("PACKET_RESULT_ID_SET_HOLD")

    approved_pairs = set()
    for row in advice:
        pair = (row.get("calibration_id"), row.get("dimension"))
        if (row.get("reviewer_type") != "AI_ADVISORY_NOT_OWNER"
                or row.get("ai_recommendation") != RECOMMENDATION
                or row.get("semantic_recheck_required") is not False
                or pair in approved_pairs or pair[0] not in result_ids
                or pair[1] not in severity.DIMENSIONS):
            stop("AI_ADVISORY_ROW_HOLD")
        approved_pairs.add(pair)

    expected_pairs = set()
    result_by_id = {row["case_ref"]: row for row in results}
    for case_ref, result in result_by_id.items():
        for dimension in severity.DIMENSIONS:
            item = result["assessments"][dimension]
            if (item["verdict"] == "NOT_SUPPORTED"
                    and item["context_coverage"]["history_complete"] is False):
                expected_pairs.add((case_ref, dimension))
    if approved_pairs != expected_pairs or len(approved_pairs) != 35:
        stop("APPROVED_PAIR_SET_MISMATCH")

    normalized, counts = normalize_results(
        results, packets, approved_pairs, severity.DIMENSIONS
    )
    if counts != {
        "history_completeness_confirmed": 35,
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
        "schema": "storyforge_r60_owner_history_completeness_owner_approval_v1",
        "status": "OWNER_APPROVED_ALL_AI_RECOMMENDATIONS",
        "approved_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "approved_recommendation_count": 35,
        "approved_dimensions": {"player_agency": 16, "safety": 19, "hard_rule": 0},
        "decision": {"history_complete": True, "verdict": "NOT_SUPPORTED",
                     "verdict_changes": 0, "semantic_rechecks_required": 0},
        "ai_advisory_sha256": sha(raw[AI_REVIEW]),
        "source_sha256": {name: sha(raw[name]) for name in REQUIRED_SHA_FILES},
        "originals_modified": False,
        "gpu_started": False,
        "training_authorized": False,
        "private_values_emitted": False,
    }
    outputs = {
        PACKET: raw[PACKET],
        RESULTS: normalized_raw,
        SEMANTIC: raw[SEMANTIC],
        SCHEMA: raw[SCHEMA],
        AI_REVIEW: raw[AI_REVIEW],
        AI_SAFE: raw[AI_SAFE],
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
        "input_sha256": {name: sha(raw[name]) for name in REQUIRED_SHA_FILES},
        "output_sha256": {name: sha((output / name).read_bytes()) for name in outputs},
        "approval_sha256": sha((output / APPROVAL).read_bytes()),
        "manifest_sha256": sha(manifest_path.read_bytes()),
        "safe_sha256": sha(safe_path.read_bytes()),
        "originals_modified": False,
        "private_values_emitted": False,
        "quality_v1_admitted": safe.get("quality_v1_admitted"),
        "training_authorized": safe.get("training_authorized"),
        "gpu_started": safe.get("gpu_started"),
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
