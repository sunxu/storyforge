#!/usr/bin/env python3
"""Validate two independent PRIVATE Gold195 pilot13 AI reviews, SAFE counts only.

No narrative text, case IDs, quoted evidence or hashes emitted. No training
dataset, source rewrites, automatic approval or protected test access.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import stat

from r58_gold195_blind_quality_pilot13 import PILOT_SCHEMA, CROSSWALK_SCHEMA
from gold195_six_dimension_review_tasks import FLOORS, RUBRIC, SEVERE
from gold195_source_review_packet import canon

OUTPUT_SCHEMA = "r58_gold195_literary_pilot13_dual_review_safe_v1"
CAP = 30 * 1024 * 1024


def read_private(path: Path, jsonl: bool):
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ValueError("PRIVATE_FILE_MISSING")
    st = path.stat()
    if (not stat.S_ISREG(st.st_mode) or stat.S_IMODE(st.st_mode) != 0o600
            or st.st_nlink != 1 or not 0 < st.st_size <= CAP):
        raise ValueError("PRIVATE_FILE_SECURITY")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as stream:
        fst = os.fstat(stream.fileno())
        if (fst.st_dev, fst.st_ino) != (st.st_dev, st.st_ino):
            raise ValueError("PRIVATE_FILE_CHANGED")
        payload = stream.read(CAP + 1)
    if len(payload) > CAP:
        raise ValueError("PRIVATE_FILE_TOO_LARGE")
    value = [json.loads(x) for x in payload.splitlines() if x.strip()] if jsonl else json.loads(payload)
    return value


def validate_response(response, material):
    if not isinstance(response, dict) or set(response) != {
        "decision", "scores", "severe_flags",
        "card_snapshot_suitable_for_offline_training",
        "card_conflicts_with_visible_history_or_gold",
        "specific_source_quotes", "specific_target_quotes",
        "literary_quality_notes", "uncertainty",
    }:
        raise ValueError("REVIEW_RESPONSE_SHAPE")
    decision = response["decision"]
    if decision not in ("PASS", "HOLD", "REJECT"):
        raise ValueError("REVIEW_DECISION_UNFILLED")
    scores = response["scores"]
    flags = response["severe_flags"]
    if (not isinstance(scores, dict) or set(scores) != set(RUBRIC)
            or not isinstance(flags, dict) or set(flags) != set(SEVERE)):
        raise ValueError("REVIEW_SCORE_OR_FLAG_SHAPE")
    for v in scores.values():
        if not (type(v) is int and 1 <= v <= 5) and not (decision == "HOLD" and v is None):
            raise ValueError("REVIEW_SCORE_INVALID")
    for v in flags.values():
        if type(v) is not bool and not (decision == "HOLD" and v is None):
            raise ValueError("REVIEW_SEVERE_UNVERIFIED")
    if any(x is True for x in flags.values()) and decision != "REJECT":
        raise ValueError("REVIEW_SEVERE_NOT_REJECTED")
    for key in ("card_snapshot_suitable_for_offline_training",
                "card_conflicts_with_visible_history_or_gold"):
        value = response[key]
        if type(value) is not bool and not (decision == "HOLD" and value is None):
            raise ValueError("REVIEW_CARD_DECISION_UNVERIFIED")
    notes = response["literary_quality_notes"]
    uncertainty = response["uncertainty"]
    if not isinstance(notes, str) or len(notes.strip()) < 8:
        raise ValueError("REVIEW_REASONING_MISSING")
    if uncertainty is not None and not isinstance(uncertainty, str):
        raise ValueError("REVIEW_UNCERTAINTY_SHAPE")
    if decision == "HOLD" and (not isinstance(uncertainty, str) or not uncertainty.strip()):
        raise ValueError("REVIEW_HOLD_UNEXPLAINED")
    history = material["messages"]
    target = material["target_text"]
    if not isinstance(history, list) or len(history) < 2 or not isinstance(target, str):
        raise ValueError("REVIEW_SOURCE_SHAPE")
    # Require PASS evidence from actual visible history, not only an unapproved card.
    source_parts = [m["content"] for m in history if m["role"] in ("user", "assistant")]
    for key, texts in (("specific_source_quotes", source_parts),
                       ("specific_target_quotes", [target])):
        quotes = response[key]
        if (not isinstance(quotes, list) or len(quotes) > 12
                or any(not isinstance(q, str) or not q.strip()
                       or len(q) > 300 or not any(q in t for t in texts)
                       for q in quotes)):
            raise ValueError("REVIEW_QUOTE_NOT_VERBATIM")
        if decision == "PASS" and not quotes:
            raise ValueError("REVIEW_PASS_EVIDENCE_MISSING")
    if decision == "PASS":
        if (response["card_snapshot_suitable_for_offline_training"] is not True
                or response["card_conflicts_with_visible_history_or_gold"] is not False
                or any(v is not False for v in flags.values())
                or any(scores[k] < floor for k, floor in FLOORS.items())):
            raise ValueError("REVIEW_PASS_BELOW_QUALITY_GATE")
    return decision


def collect(original, completed):
    if not isinstance(original, list) or not isinstance(completed, list):
        raise ValueError("REVIEW_NOT_JSONL")
    if len(original) != 13 or len(completed) != 13:
        raise ValueError("REVIEW_EXPECTED_13")
    original_by_id = {}
    for row in original:
        if (not isinstance(row, dict) or row.get("schema") != PILOT_SCHEMA
                or not isinstance(row.get("blind_id"), str) or not row["blind_id"]
                or row.get("training_authorized") is not False
                or row.get("quality_v1_admitted") is not False
                or any(v is not None for v in row.get("response", {}).get("scores", {}).values())
                or row.get("response", {}).get("decision") is not None):
            raise ValueError("REVIEW_SOURCE_CONTRACT")
        identity = row["blind_id"]
        if identity in original_by_id:
            raise ValueError("REVIEW_DUPLICATE_SOURCE")
        original_by_id[identity] = row
    decisions = {}
    for row in completed:
        if not isinstance(row, dict) or row.get("blind_id") not in original_by_id:
            raise ValueError("REVIEW_UNKNOWN_OR_DUPLICATE_CASE")
        identity = row["blind_id"]
        if identity in decisions:
            raise ValueError("REVIEW_DUPLICATE_COMPLETED")
        orig = original_by_id[identity]
        if set(orig) != set(row) or any(row[k] != orig[k] for k in orig if k != "response"):
            raise ValueError("REVIEW_SOURCE_MUTATED")
        decisions[identity] = validate_response(row["response"], orig)
    if set(decisions) != set(original_by_id):
        raise ValueError("REVIEW_CASE_SET_MISMATCH")
    return original_by_id, decisions


def analyze(a_source, a_done, b_source, b_done, crosswalk):
    a_orig, a_decisions = collect(a_source, a_done)
    b_orig, b_decisions = collect(b_source, b_done)
    if (not isinstance(crosswalk, dict) or crosswalk.get("schema") != CROSSWALK_SCHEMA
            or crosswalk.get("quality_v1_admitted") != 0
            or crosswalk.get("training_authorized") is not False
            or not isinstance(crosswalk.get("selected"), list)
            or len(crosswalk["selected"]) != 13):
        raise ValueError("CROSSWALK_INVALID")
    seen_a, seen_b, worlds, targets = set(), set(), set(), set()
    pairs = []
    for link in crosswalk["selected"]:
        ai, bi = link["reviewer_a_blind_id"], link["reviewer_b_blind_id"]
        if ai in seen_a or bi in seen_b or ai not in a_orig or bi not in b_orig:
            raise ValueError("CROSSWALK_CASE_ID_INVALID")
        seen_a.add(ai)
        seen_b.add(bi)
        world = link["story_uuid"]
        target_sha = link["source_target_sha256"]
        card_sha = link["card_snapshot_sha256"]
        if world in worlds or target_sha in targets:
            raise ValueError("CROSSWALK_DUPLICATE_WORLD_OR_TARGET")
        worlds.add(world)
        targets.add(target_sha)
        original_a = a_orig[ai]
        original_b = b_orig[bi]
        if (canon(original_a["messages"]) != canon(original_b["messages"])
                or original_a["target_text"] != original_b["target_text"]
                or hashlib.sha256(original_a["target_text"].encode("utf-8")).hexdigest() != target_sha
                or hashlib.sha256(original_a["messages"][0]["content"].encode("utf-8")).hexdigest() != card_sha):
            raise ValueError("CROSSWALK_SOURCE_CONTENT_MISMATCH")
        pairs.append((a_decisions[ai], b_decisions[bi]))
    if seen_a != set(a_orig) or seen_b != set(b_orig):
        raise ValueError("CROSSWALK_COVERAGE_MISMATCH")
    counts_a = Counter(x for x, _ in pairs)
    counts_b = Counter(y for _, y in pairs)
    both_pass = sum(x == "PASS" and y == "PASS" for x, y in pairs)
    return {
        "schema": OUTPUT_SCHEMA,
        "status": "GOLD195_PILOT13_DUAL_REVIEW_STRUCTURALLY_VALID__QUALITY_NOT_ADMITTED",
        "source_world_ids": 13,
        "reviewer_cases_each": 13,
        "reviewer_a": {k: counts_a[k] for k in ("PASS", "HOLD", "REJECT")},
        "reviewer_b": {k: counts_b[k] for k in ("PASS", "HOLD", "REJECT")},
        "same_decision_pairs": sum(x == y for x, y in pairs),
        "disagreed_pairs": sum(x != y for x, y in pairs),
        "both_pass_review_only": both_pass,
        "any_hold_or_reject": len(pairs) - both_pass,
        "reviewer_independence_proven_by_validator": False,
        "card_semantic_authority_independently_verified": False,
        "world_component_isolation_certified": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "private_text_or_ids_emitted": False,
    }


def main():
    p = argparse.ArgumentParser()
    for arg in ("reviewer-a-source", "reviewer-a-completed", "reviewer-b-source",
                "reviewer-b-completed", "owner-crosswalk"):
        p.add_argument("--" + arg, type=Path, required=True)
    a = p.parse_args()
    try:
        result = analyze(
            read_private(a.reviewer_a_source, True),
            read_private(a.reviewer_a_completed, True),
            read_private(a.reviewer_b_source, True),
            read_private(a.reviewer_b_completed, True),
            read_private(a.owner_crosswalk, False),
        )
        code = 0
    except Exception:
        result = {
            "schema": OUTPUT_SCHEMA,
            "status": "GOLD195_PILOT13_REVIEW_VALIDATION_HOLD",
            "quality_v1_admitted": 0, "training_authorized": False,
            "private_text_or_ids_emitted": False,
        }
        code = 42
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
