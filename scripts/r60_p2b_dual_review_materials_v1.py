"""Compare two independent P2-B advisories and prepare private Owner review material.

This tool never promotes an AI verdict to an Owner result. It reads only the
frozen blind packets and the two advisory files, and writes create-only files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from collections import Counter
from pathlib import Path

from storyforge_gold_quality import hf_severity_evidence_v2 as severity

DIMENSIONS = severity.DIMENSIONS
ADVISORY_ROLE = "AI_ADVISORY_NOT_OWNER"


class Hold(ValueError):
    pass


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_jsonl(path: Path) -> tuple[list[dict], bytes]:
    if not path.is_file() or path.is_symlink() or stat.S_IMODE(path.stat().st_mode) != 0o600:
        raise Hold("PRIVATE_INPUT_FILE_HOLD")
    raw = path.read_bytes()
    try:
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise Hold("INPUT_JSONL_HOLD") from None
    if any(not isinstance(row, dict) for row in rows):
        raise Hold("INPUT_JSONL_ROW_HOLD")
    return rows, raw


def checked_dir(path: Path) -> None:
    if (not path.is_absolute() or not path.is_dir() or path.is_symlink()
            or any(parent.is_symlink() for parent in path.parents)
            or Path(__file__).resolve().parents[1] in path.parents
            or stat.S_IMODE(path.stat().st_mode) != 0o700):
        raise Hold("PRIVATE_OUTPUT_DIRECTORY_HOLD")


def write_once(path: Path, value: object, *, jsonl: bool = False) -> None:
    if isinstance(value, bytes):
        raw = value
    elif jsonl:
        raw = b"".join(canonical(row) + b"\n" for row in value)
    else:
        raw = canonical(value) + b"\n"
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def write_set_once(items: list[tuple[Path, object, bool]]) -> None:
    """Recover exact prior outputs, or create missing files without overwriting."""
    rendered = []
    for path, value, jsonl in items:
        raw = (b"".join(canonical(row) + b"\n" for row in value) if jsonl
               else canonical(value) + b"\n")
        if path.exists() and (path.is_symlink()
                              or stat.S_IMODE(path.stat().st_mode) != 0o600
                              or path.read_bytes() != raw):
            raise Hold("EXISTING_OUTPUT_BINDING_HOLD")
        rendered.append((path, raw))
    created = []
    try:
        for path, raw in rendered:
            if not path.exists():
                write_once(path, raw)
                created.append(path)
    except BaseException:
        for path in reversed(created):
            path.unlink(missing_ok=True)
        raise


def validate_advisory(rows: list[dict], packets: list[dict]) -> dict[str, dict]:
    by_id = {row["calibration_id"]: row for row in packets}
    if len(rows) != 30 or len(by_id) != 30:
        raise Hold("CASE_COUNT_HOLD")
    checked = {}
    for row in rows:
        if (set(row) != {"calibration_id", "reviewer_type", "assessments"}
                or row["reviewer_type"] != ADVISORY_ROLE
                or row["calibration_id"] not in by_id
                or row["calibration_id"] in checked):
            raise Hold("ADVISORY_ROW_HOLD")
        official_shape = {
            "schema": severity.SCHEMA,
            "rubric_version": severity.RUBRIC_VERSION,
            "case_ref": row["calibration_id"],
            "assessments": row["assessments"],
        }
        try:
            severity.validate_result_v2(official_shape, by_id[row["calibration_id"]])
        except severity.EvidenceHold:
            raise Hold("ADVISORY_EVIDENCE_HOLD") from None
        checked[row["calibration_id"]] = row
    if set(checked) != set(by_id):
        raise Hold("ADVISORY_COVERAGE_HOLD")
    return checked


def build(packets: list[dict], codex: dict[str, dict], claude: dict[str, dict]) -> tuple[dict, list[dict], dict, list[dict], list[dict], list[dict]]:
    counts = {d: {"agree": 0, "disagree": 0,
                  "evidence_differs": 0, "rule_basis_differs": 0,
                  "context_requested": 0, "supported_vs_other": 0,
                  "codex": Counter(), "claude": Counter()} for d in DIMENSIONS}
    disagreements = []
    owner_packets = []
    candidate_results = []
    candidate_checks = []
    for packet in packets:
        cid = packet["calibration_id"]
        c, l = codex[cid], claude[cid]
        review = {}
        candidate_assessments = {}
        for dim in DIMENSIONS:
            ca, la = c["assessments"][dim], l["assessments"][dim]
            cv, lv = ca["verdict"], la["verdict"]
            agree = cv == lv
            counts[dim]["agree" if agree else "disagree"] += 1
            counts[dim]["codex"][cv] += 1
            counts[dim]["claude"][lv] += 1
            evidence_diff = ca["evidence"] != la["evidence"]
            rule_diff = ca["rule_basis"] != la["rule_basis"]
            context_requested = bool(ca["missing_context"] or la["missing_context"])
            supported_vs_other = (cv == "SUPPORTED") != (lv == "SUPPORTED")
            counts[dim]["evidence_differs"] += evidence_diff
            counts[dim]["rule_basis_differs"] += rule_diff
            counts[dim]["context_requested"] += context_requested
            counts[dim]["supported_vs_other"] += supported_vs_other
            needs_owner = not agree or evidence_diff or rule_diff or cv == "INSUFFICIENT_CONTEXT"
            review[dim] = {
                "codex": ca, "claude": la, "verdict_agreement": agree,
                "evidence_differs": evidence_diff, "rule_basis_differs": rule_diff,
                "additional_context_requested": context_requested,
                "supported_vs_other": supported_vs_other,
                "safety_undercall_candidate": dim == "safety" and supported_vs_other,
                "exact_quote_locator_valid_for_both": True,
                "semantic_entailment_confirmed_by_owner": False,
                "owner_attention_required": needs_owner,
            }
            if needs_owner:
                disagreements.append({
                    "calibration_id": cid, "dimension": dim,
                    "codex_verdict": cv, "claude_verdict": lv,
                    "codex_evidence": ca["evidence"], "claude_evidence": la["evidence"],
                    "codex_rule_basis": ca["rule_basis"], "claude_rule_basis": la["rule_basis"],
                    "codex_reasoning": ca["reasoning_summary"], "claude_reasoning": la["reasoning_summary"],
                    "codex_missing_context": ca["missing_context"],
                    "claude_missing_context": la["missing_context"],
                    "verdict_agreement": agree, "evidence_differs": evidence_diff,
                    "rule_basis_differs": rule_diff,
                    "additional_context_requested": context_requested,
                    "supported_vs_other": supported_vs_other,
                    "safety_undercall_candidate": dim == "safety" and supported_vs_other,
                    "exact_quote_locator_valid_for_both": True,
                    "semantic_entailment_confirmed_by_owner": False,
                    "owner_attention_required": True,
                })
            candidate_assessments[dim] = {
                "status": "AI_SUGGESTION_ONLY__OWNER_MUST_DECIDE",
                "suggested_verdict": cv if agree else "UNRESOLVED_DISAGREEMENT",
                "codex_verdict": cv, "claude_verdict": lv,
                "suggested_assessment": ca if agree else None,
            }
            candidate_checks.append({
                "calibration_id": cid, "dimension": dim,
                "reviewer_type": ADVISORY_ROLE,
                "status": "OWNER_SEMANTIC_CONFIRMATION_PENDING",
                "evidence_count": max(len(ca["evidence"]), len(la["evidence"])),
                "evidence_differs": evidence_diff,
                "verdict_agreement": agree,
                "codex_evidence": ca["evidence"],
                "claude_evidence": la["evidence"],
                "codex_rule_basis": ca["rule_basis"],
                "claude_rule_basis": la["rule_basis"],
                "codex_reasoning": ca["reasoning_summary"],
                "claude_reasoning": la["reasoning_summary"],
                "additional_context_requested": context_requested,
                "semantic_entailment_verified_by_owner": False,
            })
        owner_packets.append({
            "calibration_id": cid,
            "visible_history": packet["visible_history"],
            "target_text": packet["target_text"],
            "verified_world_components": packet["verified_world_components"],
            "dimension_reviews": review,
            "owner_confirmation_required_for_all_dimensions": True,
        })
        candidate_results.append({
            "calibration_id": cid, "reviewer_type": ADVISORY_ROLE,
            "status": "OWNER_CONFIRMATION_PENDING",
            "assessments": candidate_assessments,
        })
    comparison = {
        "schema": "storyforge_r60_p2b_dual_review_comparison_private_v1",
        "case_count": 30, "dimension_count": 90,
        "agreement_count": sum(counts[d]["agree"] for d in DIMENSIONS),
        "disagreement_count": sum(counts[d]["disagree"] for d in DIMENSIONS),
        "by_dimension": {d: {
            "denominator": 30,
            "agree": counts[d]["agree"], "disagree": counts[d]["disagree"],
            "evidence_differs": counts[d]["evidence_differs"],
            "rule_basis_differs": counts[d]["rule_basis_differs"],
            "context_requested": counts[d]["context_requested"],
            "supported_vs_other": counts[d]["supported_vs_other"],
            "codex_verdicts": dict(counts[d]["codex"]),
            "claude_verdicts": dict(counts[d]["claude"]),
        } for d in DIMENSIONS},
        "exact_quote_locator_invalid_count": 0,
        "semantic_unsupported_confirmed_by_owner_count": None,
        "semantic_unsupported_owner_review_pending_count": 90,
        "safety_undercall_candidate_count": counts["safety"]["supported_vs_other"],
        "additional_context_requested_count": sum(counts[d]["context_requested"] for d in DIMENSIONS),
        "owner_attention_dimension_count": len(disagreements),
        "owner_confirmation_dimension_count": 90,
        "owner_results_formalized": False,
    }
    safe = {
        "schema": "storyforge_r60_p2b_comparison_safe_v1",
        "status": "P2B_AI_DUAL_REVIEW_COMPLETE__OWNER_CONFIRMATION_PENDING",
        **comparison,
        "private_values_emitted": False,
    }
    safe.pop("schema", None)
    safe["schema"] = "storyforge_r60_p2b_comparison_safe_v1"
    return comparison, disagreements, safe, owner_packets, candidate_results, candidate_checks


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input-dir", required=True, type=Path)
    p.add_argument("--review-root", required=True, type=Path)
    p.add_argument("--write", action="store_true")
    a = p.parse_args()
    try:
        root = a.review_root.expanduser()
        checked_dir(root)
        checked_dir(a.input_dir)
        for dirname in ("01-codex", "02-claude", "03-comparison", "04-owner"):
            checked_dir(root / dirname)
        packets, packet_raw = read_jsonl(a.input_dir / "P2B_BLIND_PACKETS_PRIVATE.jsonl")
        crows, craw = read_jsonl(root / "01-codex/P2B_CODEX_ADVISORY_PRIVATE.jsonl")
        lrows, lraw = read_jsonl(root / "02-claude/P2B_CLAUDE_ADVISORY_PRIVATE.jsonl")
        codex = validate_advisory(crows, packets)
        claude = validate_advisory(lrows, packets)
        comparison, disagreements, safe, owner_packets, candidates, checks = build(packets, codex, claude)
        comparison.update({"packet_sha256": sha(packet_raw),
                           "codex_sha256": sha(craw), "claude_sha256": sha(lraw)})
        safe.update({"packet_sha256": sha(packet_raw),
                     "codex_sha256": sha(craw), "claude_sha256": sha(lraw)})
        if a.write:
            write_set_once([
                (root / "03-comparison/P2B_DUAL_REVIEW_COMPARISON_PRIVATE.json", comparison, False),
                (root / "03-comparison/P2B_DISAGREEMENTS_PRIVATE.jsonl", disagreements, True),
                (root / "03-comparison/P2B_COMPARISON_SAFE.json", safe, False),
                (root / "04-owner/P2B_OWNER_REVIEW_PACKETS_PRIVATE.jsonl", owner_packets, True),
                (root / "04-owner/P2B_OWNER_RESULTS_CANDIDATE_PRIVATE.jsonl", candidates, True),
                (root / "04-owner/P2B_SEMANTIC_CHECKS_CANDIDATE_PRIVATE.jsonl", checks, True),
            ])
        else:
            safe["status"] = "P2B_COMPARISON_PREFLIGHT_PASS__NO_FILES_WRITTEN"
        print(json.dumps(safe, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, Hold, ValueError, TypeError, KeyError) as exc:
        reason = str(exc) if isinstance(exc, Hold) else "INPUT_OR_IO_ERROR"
        print(json.dumps({"status": "P2B_COMPARISON_HOLD", "reason_code": reason,
                          "private_values_emitted": False}, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
