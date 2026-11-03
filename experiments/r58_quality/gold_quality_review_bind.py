"""Owner-local Gold192 review-to-Quality-v1 evidence binder; NO admission.

Requires pinned canonical A/B/exclusion files and independently supplied,
case-specific Owner evidence. Never invents world/rights/independence evidence.
Reads no database or R50; only emits aggregate counts to stdout.
"""
from __future__ import annotations

import argparse
import json
import re
import stat
from collections import Counter
from pathlib import Path

from gold_source_context_stage import StageHold, _create_only, _private_file, _read_rows
from quality_v1 import EVIDENCE, SCHEMA, SEVERE, canonical, decide, sha, summarize
from r59_gold192_supabase_extract import A_SHA, B_SHA, EX_SHA

SAFE_SCHEMA = "storyforge-gold192-review-bind-safe-v1"
HEX = re.compile(r"^[a-f0-9]{64}$")
MAX_BYTES = 40 * 1024 * 1024


class BindHold(ValueError):
    pass


def _index(rows, label, *, case_key=None):
    result = {}
    for row in rows:
        if not isinstance(row, dict):
            raise BindHold("SOURCE_ROW_INVALID")
        digest = row.get("target_sha256")
        if not isinstance(digest, str) or HEX.fullmatch(digest) is None or digest in result:
            raise BindHold("SOURCE_DIGEST_DUPLICATE_OR_INVALID")
        if case_key is not None and (not isinstance(row.get(case_key), str)
                                     or not row[case_key]):
            raise BindHold("SOURCE_CASE_ID_INVALID")
        result[digest] = row
    return result


def _private_input(path, label):
    try:
        return _private_file(path, MAX_BYTES)
    except StageHold as exc:
        raise BindHold(f"{label}_{exc}") from None


def _file(path, digest=None, *, label="SOURCE"):
    raw = _private_input(path, label)
    if digest is not None and sha(raw) != digest:
        raise BindHold("PINNED_SOURCE_MISMATCH")
    try:
        return json.loads(raw)
    except (ValueError, UnicodeError):
        raise BindHold("SOURCE_JSON_INVALID") from None


def _jsonl_or_json_file(path, digest, *, label):
    raw = _private_input(path, label)
    if sha(raw) != digest:
        raise BindHold("PINNED_SOURCE_MISMATCH")
    try:
        try:
            parsed = json.loads(raw)
        except (ValueError, UnicodeError):
            parsed = [
                json.loads(line)
                for line in raw.splitlines()
                if line.strip()
            ]
        if not isinstance(parsed, list) or any(
            not isinstance(row, dict) for row in parsed
        ):
            raise ValueError
        return parsed
    except (ValueError, UnicodeError):
        raise BindHold(f"{label}_JSON_OR_JSONL_INVALID") from None


def _owner_index(rows):
    indexed = {}
    for row in rows:
        if not isinstance(row, dict):
            raise BindHold("OWNER_EVIDENCE_FORMAT_INVALID")
        cid = row.get("case_id")
        if not isinstance(cid, str) or not cid or cid in indexed:
            raise BindHold("OWNER_CASE_DUPLICATE_OR_INVALID")
        indexed[cid] = row
    return indexed


def _a_scores(row):
    # Frozen A v3 has both scored and aggregate-complement PASS_ONLY entries.
    scores = row.get("scores_1_to_5")
    if scores is None:
        scores = row.get("reviewer_a_scores_1_to_5")
    if row.get("aggregate_complement_only") is True:
        return None
    if row.get("evidence_granularity") not in (None, "CASE_LEVEL_SCORED_REVIEW"):
        return None
    if row.get("case_level_scored_review_present") is False:
        return None
    if row.get("decision_for_strict_ab_pairing",
               row.get("reported_final_decision")) != "PASS_ONLY":
        return None
    return scores if isinstance(scores, dict) else None


def _bind_one(stage, owner, a, b, excluded, pins):
    cid = stage["case_id"]
    target_hash = stage["target_sha256"]
    if (not isinstance(owner, dict) or owner.get("case_id") != cid
            or owner.get("target_sha256") != target_hash
            or owner.get("story_id") != stage.get("story_id")
            or owner.get("session_id") != stage.get("session_id")):
        return None, "OWNER_EVIDENCE_MISSING_OR_IDENTITY_MISMATCH"
    if target_hash in excluded:
        return None, "EXCLUDED_BY_FROZEN_DISAGREEMENT_SET"
    if (stage.get("status") != "SOURCE_CONTEXT_STAGED__QUALITY_REVIEW_PENDING"
            or stage.get("schema") != "storyforge-quality-v1-source-staging-private-v1"):
        return None, "SOURCE_STAGE_NOT_READY"
    if a is None or b is None or a.get("case_id") != cid:
        return None, "REVIEW_SOURCE_MISSING_OR_MISMATCH"
    if b.get("decision") != "PASS":
        return None, "REVIEWER_B_NOT_PASS"
    scores_a = _a_scores(a)
    scores_b = b.get("scores_1_to_5")
    if scores_a is None or not isinstance(scores_b, dict):
        return None, "CASE_LEVEL_SCORES_MISSING"
    if b.get("severe_flags") != []:
        return None, "REVIEWER_B_SEVERE_OR_UNVERIFIED"
    owner_flags = owner.get("owner_supplemental_severe_flags")
    owner_safety_ref = owner.get("owner_supplemental_severe_evidence_ref")
    if (not isinstance(owner_flags, dict) or set(owner_flags) != set(SEVERE)
            or any(type(v) is not bool for v in owner_flags.values())
            or not isinstance(owner_safety_ref, str) or not owner_safety_ref.strip()):
        return None, "OWNER_SUPPLEMENTAL_SEVERE_FLAGS_UNVERIFIED"
    if any(owner_flags.values()):
        return None, "OWNER_SUPPLEMENTAL_SEVERE_FLAG_PRESENT"
    flags_a = a.get("severe_flags")
    if flags_a is not None and (
        not isinstance(flags_a, list) or flags_a
    ):
        return None, "REVIEWER_A_SEVERE_OR_UNVERIFIED"
    evidence = owner.get("evidence")
    if (not isinstance(evidence, dict)
            or any(evidence.get(k) is not True for k in EVIDENCE)
            or any(evidence.get(k) is not False for k in (
                "known_protected_overlap", "final_heldout_overlap",
                "protected_test_body_accessed",
            ))):
        return None, "OWNER_REQUIRED_EVIDENCE_INCOMPLETE"
    if (not isinstance(owner.get("world_component_id"), str)
            or not owner["world_component_id"]
            or owner.get("split") not in ("train", "validation")
            or any(not isinstance(owner.get(key), str)
                   or HEX.fullmatch(owner[key]) is None
                   for key in ("world_graph_sha256", "source_version_sha256"))):
        return None, "WORLD_SPLIT_OR_SOURCE_PIN_UNRESOLVED"
    # These are distinct pins: the frozen original Gold source-version SHA is
    # owner-provided, while staging/source-context file pins are byte-checked.
    # They must never be substituted for one another.
    if (owner.get("staged_file_sha256") != pins["staged_file_sha256"]
            or owner.get("source_context_file_sha256") != pins["source_context_file_sha256"]):
        return None, "OWNER_SOURCE_CONTEXT_PINS_MISMATCH"
    if (not isinstance(owner.get("reviewer_a_evidence_ref"), str)
            or not owner["reviewer_a_evidence_ref"]
            or not isinstance(owner.get("reviewer_b_evidence_ref"), str)
            or not owner["reviewer_b_evidence_ref"]):
        return None, "REVIEWER_EVIDENCE_REF_MISSING"
    if not isinstance(stage.get("messages"), list):
        return None, "SOURCE_MESSAGES_UNAVAILABLE"
    row = {
        "schema": SCHEMA,
        "case_id": cid,
        "corpus": "gold195",
        "source_kind": "original_gold",
        "source_version_sha256": owner["source_version_sha256"],
        "world_graph_sha256": owner["world_graph_sha256"],
        "world_component_id": owner["world_component_id"],
        "split": owner["split"],
        "messages": stage["messages"],
        "target_text": stage["target_text"],
        "input_messages_sha256": stage["input_messages_sha256"],
        "assistant_target_sha256": target_hash,
        "evidence": evidence,
        "reviews": [
            {
                "reviewer_key": "reviewer_a",
                "decision": "PASS",
                "scores": scores_a,
                "severe_flags": (
                    {key: False for key in SEVERE}
                    if isinstance(flags_a, list) and not flags_a else None
                ),
                "private_evidence_ref": owner["reviewer_a_evidence_ref"],
            },
            {
                "reviewer_key": "reviewer_b",
                "decision": "PASS",
                "scores": scores_b,
                "severe_flags": {k: False for k in SEVERE},
                "private_evidence_ref": owner["reviewer_b_evidence_ref"],
            },
        ],
        "owner_supplemental_safety_review": {
            "scope": "SUPPLEMENTAL_SEVERE_FLAG_SCREEN",
            "decision": "PASS",
            "severe_flags": owner_flags,
            "private_evidence_ref": owner_safety_ref,
        },
    }
    verdict, reason = decide(row)
    if verdict != "PASS":
        return None, "QUALITY_V1_" + reason
    return row, None


def bind(staged, a_doc, b_doc, exclusions, owner_rows, staged_sha,
         source_context_sha):
    if (not isinstance(staged, list) or not 1 <= len(staged) <= 192
            or not isinstance(a_doc, dict) or not isinstance(b_doc, dict)
            or not isinstance(exclusions, list) or len(exclusions) != 11):
        raise BindHold("SOURCE_COUNTS_INVALID")
    aa, bb = a_doc.get("records"), b_doc.get("cases")
    if not isinstance(aa, list) or not isinstance(bb, list):
        raise BindHold("REVIEW_STRUCTURE_INVALID")
    a, b, ex = _index(aa, "A", case_key="case_id"), _index(bb, "B"), _index(exclusions, "EX")
    if (len(a) != 192 or len(b) != 192 or len(ex) != 11
            or set(a) != set(b) or not set(ex) <= set(a)
            or any(x.get("exclusion_reason") != "EXCLUDED_FROM_TRAINING_DISAGREEMENT"
                   for x in exclusions)):
        raise BindHold("FROZEN_REVIEW_COVERAGE_INVALID")
    owner = _owner_index(owner_rows)
    if len({x.get("case_id") for x in staged if isinstance(x, dict)}) != len(staged):
        raise BindHold("STAGING_CASE_ID_DUPLICATE")
    result, reasons = [], Counter()
    source_stage_reasons = Counter()
    stage_ready = 0
    stage_ids = set()
    for row in staged:
        if not isinstance(row, dict):
            raise BindHold("STAGING_ROW_INVALID")
        cid = row.get("case_id")
        digest = row.get("target_sha256")
        if (not isinstance(cid, str) or not cid
                or not isinstance(digest, str) or digest not in a):
            raise BindHold("STAGING_SOURCE_IDENTITY_INVALID")
        stage_ids.add(cid)
        if (row.get("schema") != "storyforge-quality-v1-source-staging-private-v1"
                or row.get("status") != "SOURCE_CONTEXT_STAGED__QUALITY_REVIEW_PENDING"):
            source_stage_reasons[row.get("private_reason_code", "SOURCE_STAGE_NOT_READY")] += 1
            continue
        stage_ready += 1
        item, reason = _bind_one(row, owner.get(cid), a[digest], b[digest], ex, {
            "staged_file_sha256": staged_sha,
            "source_context_file_sha256": source_context_sha,
        })
        if item is None:
            reasons[reason] += 1
        else:
            result.append(item)
    if not set(owner) <= stage_ids:
        raise BindHold("OWNER_EVIDENCE_OUTSIDE_STAGE")
    if result:
        summary = summarize(result)
        if (summary["decision_counts"]["PASS"] != len(result)
                or summary["world_train_validation_collision_found"]):
            raise BindHold("WORLD_OR_DUPLICATE_CANDIDATE_COLLISION")
    result.sort(key=lambda x: x["case_id"])
    return result, {
        "schema": SAFE_SCHEMA,
        "status": "REVIEW_EVIDENCE_BOUND__CANDIDATES_NOT_ADMITTED",
        "input_staged": len(staged),
        "source_stage_ready": stage_ready,
        "source_stage_held": len(staged) - stage_ready,
        "source_stage_hold_reasons": dict(sorted(source_stage_reasons.items())),
        "review_bound_candidates": len(result),
        "review_candidate_held": stage_ready - len(result),
        "held": len(staged) - len(result),
        "hold_reasons": dict(sorted(reasons.items())),
        "reviewer_independence_independently_proven": False,
        "source_context_independently_authenticated": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "r50_accessed": False,
        "private_values_emitted": False,
    }


def run(stage_path, receipt_path, a_path, b_path, exclusion_path,
        owner_path, output_dir):
    raw = _private_input(stage_path, "STAGED_JSONL")
    receipt = _file(receipt_path, label="STAGING_SAFE")
    if (receipt.get("schema") != "storyforge-gold-quality-supabase-source-stage-safe-v1"
            or receipt.get("staged_file_sha256") != sha(raw)):
        raise BindHold("STAGING_RECEIPT_MISMATCH")
    a = _file(a_path, A_SHA, label="REVIEWER_A")
    b = _file(b_path, B_SHA, label="REVIEWER_B")
    exclusions = _jsonl_or_json_file(exclusion_path, EX_SHA, label="EXCLUSIONS")
    owner = _read_rows(_private_input(owner_path, "OWNER_EVIDENCE"))
    stage = _read_rows(raw)
    upstream = receipt.get("source_context_file_sha256")
    if not isinstance(upstream, str) or HEX.fullmatch(upstream) is None:
        raise BindHold("SOURCE_CONTEXT_RECEIPT_PIN_INVALID")
    result, safe = bind(stage, a, b, exclusions, owner, sha(raw), upstream)
    if output_dir.exists() or output_dir.is_symlink():
        raise BindHold("OUTPUT_EXISTS")
    if output_dir.resolve().is_relative_to(Path.cwd().resolve()):
        raise BindHold("OUTPUT_INSIDE_REPO")
    if (not output_dir.parent.is_dir() or output_dir.parent.is_symlink()
            or stat.S_IMODE(output_dir.parent.stat().st_mode) != 0o700):
        raise BindHold("OUTPUT_PARENT_INVALID")
    output_dir.mkdir(mode=0o700)
    try:
        blob = b"".join(canonical(row) + b"\n" for row in result)
        safe["reviewed_candidates_file_sha256"] = _create_only(
            output_dir / "OWNER_REVIEWED_GOLD_CANDIDATES.jsonl", blob
        )
        _create_only(
            output_dir / "GOLD_REVIEW_BIND_SAFE.json",
            json.dumps(safe, sort_keys=True, indent=2).encode() + b"\n"
        )
    except BaseException:
        for p in output_dir.iterdir():
            p.unlink()
        output_dir.rmdir()
        raise
    return safe


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for flag in ("staged-jsonl", "staging-safe", "reviewer-a",
                 "reviewer-b", "exclusions", "owner-evidence-jsonl", "output-dir"):
        p.add_argument("--" + flag, type=Path, required=True)
    args = p.parse_args()
    try:
        safe = run(args.staged_jsonl, args.staging_safe, args.reviewer_a,
                   args.reviewer_b, args.exclusions, args.owner_evidence_jsonl,
                   args.output_dir)
        print(json.dumps(safe, sort_keys=True))
        return 0
    except (BindHold, StageHold) as exc:
        # These are fixed internal reason codes, never paths or private values.
        reason_code = str(exc)
    except OSError:
        reason_code = "INPUT_OR_OUTPUT_IO_ERROR"
    except Exception:  # noqa: BLE001 - never emit private exception strings
        reason_code = "UNEXPECTED_INTERNAL_ERROR"
    print(json.dumps({
        "schema": SAFE_SCHEMA, "status": "REVIEW_BIND_HOLD",
        "reason_code": reason_code,
        "quality_v1_admitted": 0, "training_authorized": False,
        "gpu_started": False, "r50_accessed": False,
        "private_values_emitted": False,
    }, sort_keys=True))
    return 42


if __name__ == "__main__":
    raise SystemExit(main())
