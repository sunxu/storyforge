#!/usr/bin/env python3
"""StoryForge Quality-v1: offline SFT candidate quality + world split preflight.

Only for Owner-reviewed private Gold195 / frozen R58 pilot candidates. Does not
inspect live production requests, R50 sealed tests, HF jobs or Git history.
Reads PRIVATE candidate text locally to validate input and target SHA256.
Outputs only SAFE aggregate counts; cannot approve/construct training files.

A PASS means metadata/structure/reviewer *declarations* are internally
consistent. The tool cannot judge literature, authenticate reviewers or prove
that the provided protected-world inventory is exhaustive.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import re
import stat

SCHEMA = "storyforge-quality-v1-private-candidate-v1"
OUT_SCHEMA = "storyforge-quality-v1-safe-summary-v1"
HEX64 = re.compile(r"^[a-f0-9]{64}$")
CORPORA = {"gold195", "r58_round1"}
SCORES = (
    "chinese_prose", "character_consistency", "npc_initiative",
    "player_agency", "rule_fidelity", "narrative_continuity",
)
FLOORS = {
    "chinese_prose": 4, "character_consistency": 4,
    "npc_initiative": 3, "player_agency": 4,
    "rule_fidelity": 4, "narrative_continuity": 4,
}
SEVERE = ("serious_player_agency", "hard_fact_or_ban", "safety_exclusion")
EVIDENCE = (
    "rights_attested", "source_version_verified", "context_is_coherent",
    "context_no_future_leakage_reviewed", "privacy_checked",
    "world_component_reviewed", "known_protected_metadata_checked",
    "other_known_reserved_metadata_checked", "final_heldout_metadata_checked",
    "reviewers_blinded_and_independent_attested", "owner_quality_approved",
)
MAX_INPUT_BYTES = 40 * 1024 * 1024
MAX_ROWS = 195
MAX_R58_ROWS = 20


class Hold(Exception):
    pass


def canonical(data: object) -> bytes:
    return json.dumps(
        data, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def valid_hash(v: object) -> bool:
    return isinstance(v, str) and HEX64.fullmatch(v) is not None


def input_is_valid(row: dict) -> bool:
    messages, target = row.get("messages"), row.get("target_text")
    if not isinstance(messages, list) or len(messages) < 2:
        return False
    if not isinstance(target, str) or not target.strip():
        return False
    if not isinstance(messages[0], dict) or messages[0].get("role") != "system":
        return False
    if not isinstance(messages[-1], dict) or messages[-1].get("role") != "user":
        return False
    for i, m in enumerate(messages):
        if not isinstance(m, dict) or set(m) != {"role", "content"}:
            return False
        if not isinstance(m["content"], str) or not m["content"].strip():
            return False
        if i and m["role"] != ("user" if i % 2 else "assistant"):
            return False
    return (
        row.get("input_messages_sha256") == sha(canonical(messages))
        and row.get("assistant_target_sha256") == sha(target.encode("utf-8"))
    )


def review_verdict(row: dict) -> tuple[str, str]:
    reviews = row.get("reviews")
    if not isinstance(reviews, list) or len(reviews) != 2:
        return "HOLD", "TWO_REVIEWS_REQUIRED"
    keys = []
    for review in reviews:
        if not isinstance(review, dict):
            return "HOLD", "REVIEW_FORMAT"
        key = review.get("reviewer_key")
        if not isinstance(key, str) or not key.strip():
            return "HOLD", "REVIEW_FORMAT"
        keys.append(key)
    if len(set(keys)) != 2:
        return "HOLD", "REVIEWER_NOT_DISTINCT"
    for review in reviews:
        decision = review.get("decision")
        flags = review.get("severe_flags")
        if not isinstance(flags, dict) or set(flags) != set(SEVERE):
            return "HOLD", "SERIOUS_FLAGS_UNVERIFIED"
        if any(not isinstance(flags[k], bool) for k in SEVERE):
            return "HOLD", "SERIOUS_FLAGS_UNVERIFIED"
        if any(flags.values()) or decision == "REJECT":
            return "REJECT", "REVIEW_SEVERE_OR_REJECT"
        if decision != "PASS":
            return "HOLD", "REVIEW_DISAGREEMENT"
        evidence_ref = review.get("private_evidence_ref")
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            return "HOLD", "REVIEW_EVIDENCE_MISSING"
        scores = review.get("scores")
        if not isinstance(scores, dict) or set(scores) != set(SCORES):
            return "HOLD", "QUALITY_SCORES_MISSING"
        if any(type(scores[k]) is not int or not 1 <= scores[k] <= 5
               for k in SCORES):
            return "HOLD", "QUALITY_SCORES_INVALID"
        if any(scores[k] < FLOORS[k] for k in SCORES):
            return "HOLD", "QUALITY_BELOW_V1_FLOOR"
    return "PASS", "TWO_REVIEWERS_QUALITY_DECLARED"


def decide(row: object) -> tuple[str, str]:
    if not isinstance(row, dict) or row.get("schema") != SCHEMA:
        return "HOLD", "BAD_SCHEMA"
    if row.get("corpus") not in CORPORA or row.get("source_kind") != "original_gold":
        return "HOLD", "UNKNOWN_OR_NONORIGINAL_SOURCE"
    if not isinstance(row.get("case_id"), str) or not row["case_id"].strip():
        return "HOLD", "CASE_ID_MISSING"
    if not isinstance(row.get("world_component_id"), str) or not row["world_component_id"].strip():
        return "HOLD", "WORLD_UNRESOLVED"
    if row.get("split") not in ("train", "validation"):
        return "HOLD", "SPLIT_UNRESOLVED"
    if not all(valid_hash(row.get(k)) for k in (
        "source_version_sha256", "input_messages_sha256",
        "assistant_target_sha256", "world_graph_sha256",
    )):
        return "HOLD", "SOURCE_DIGEST_MISSING"
    if not input_is_valid(row):
        return "HOLD", "INPUT_TARGET_STRUCTURE_OR_HASH_MISMATCH"
    e = row.get("evidence")
    if not isinstance(e, dict) or any(e.get(k) is not True for k in EVIDENCE):
        return "HOLD", "SOURCE_ISOLATION_OR_APPROVAL_EVIDENCE_MISSING"
    if e.get("known_protected_overlap") is not False:
        return "HOLD", "KNOWN_PROTECTED_OVERLAP_UNRESOLVED"
    if e.get("final_heldout_overlap") is not False:
        return "HOLD", "FINAL_HELDOUT_OVERLAP_UNRESOLVED"
    if e.get("protected_test_body_accessed") is not False:
        return "HOLD", "PROTECTED_TEST_CONTENT_BOUNDARY_UNVERIFIED"
    return review_verdict(row)


def summarize(rows: list[dict]) -> dict:
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_ROWS:
        raise Hold("invalid bounded candidate count")
    r58_count = sum(isinstance(r, dict) and r.get("corpus") == "r58_round1" for r in rows)
    if r58_count > MAX_R58_ROWS:
        raise Hold("R58 frozen pilot candidate cap exceeded")
    decisions = [decide(r) for r in rows]
    ids, inputs, targets = defaultdict(list), defaultdict(list), defaultdict(list)
    worlds = defaultdict(set)
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        for name, mapping in (
            ("case_id", ids), ("input_messages_sha256", inputs),
            ("assistant_target_sha256", targets),
        ):
            value = row.get(name)
            if isinstance(value, str) and value.strip():
                mapping[value].append(i)
        world, split = row.get("world_component_id"), row.get("split")
        if isinstance(world, str) and world.strip() and split in ("train", "validation"):
            worlds[world].add(split)
    conflicted = set()
    for mapping in (ids, inputs, targets):
        for indexes in mapping.values():
            if len(indexes) > 1:
                conflicted.update(indexes)
    world_conflict = {w for w, splits in worlds.items() if len(splits) > 1}
    for i, row in enumerate(rows):
        if i in conflicted:
            decisions[i] = ("HOLD", "DUPLICATE_SOURCE_OR_TARGET")
        elif isinstance(row, dict) and row.get("world_component_id") in world_conflict:
            decisions[i] = ("HOLD", "TRAIN_VALIDATION_WORLD_COLLISION")
    totals = Counter(v for v, _ in decisions)
    reasons = Counter(reason for decision, reason in decisions if decision != "PASS")
    return {
        "schema": OUT_SCHEMA,
        "status": "QUALITY_V1_STRUCTURAL_REVIEW_CANDIDATES_ONLY__NO_TRAINING_ADMISSION",
        "records_checked": len(rows),
        "gold195_candidate_count": sum(
            isinstance(r, dict) and r.get("corpus") == "gold195" for r in rows
        ),
        "r58_pilot_candidate_count": r58_count,
        "decision_counts": {k: totals[k] for k in ("PASS", "HOLD", "REJECT")},
        "hold_reject_reasons": dict(sorted(reasons.items())),
        "world_train_validation_collision_found": bool(world_conflict),
        "reviewer_independence_independently_proven": False,
        "protected_world_registry_completeness_independently_proven": False,
        "literary_quality_independently_judged_by_this_script": False,
        "tokenizer_collator_last_round_checked": False,
        "private_ids_text_or_hashes_exported": False,
        "original_provider_request_replay_required": False,
        "no_dataset_written": True,
        "g1_legacy": "HOLD", "g2_legacy": "HOLD",
        "quality_dataset_admitted": 0, "training_authorized": False,
        "expansion_allowed": False,
    }


def read_private(path: Path) -> list[dict]:
    if path.is_symlink() or not path.is_file():
        raise Hold("private input must be a regular non-symlink file")
    before = path.stat()
    if (not stat.S_ISREG(before.st_mode) or stat.S_IMODE(before.st_mode) != 0o600
            or before.st_nlink != 1 or not 0 < before.st_size <= MAX_INPUT_BYTES):
        raise Hold("private source permissions or size invalid")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, "rb") as handle:
        info = os.fstat(handle.fileno())
        if info.st_ino != before.st_ino or info.st_dev != before.st_dev:
            raise Hold("private input changed while opening")
        data = handle.read(MAX_INPUT_BYTES + 1)
    if len(data) > MAX_INPUT_BYTES:
        raise Hold("private input oversized")
    try:
        rows = [json.loads(line) for line in data.splitlines() if line.strip()]
    except (ValueError, UnicodeError, TypeError) as exc:
        raise Hold("private JSONL malformed") from exc
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-reviewed-jsonl", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(summarize(read_private(args.private_reviewed_jsonl)),
                         sort_keys=True, ensure_ascii=False, indent=2))
        return 0
    except Exception:
        # Never echo private paths, raw values, parser exception text or stacktraces.
        print(json.dumps({
            "schema": OUT_SCHEMA,
            "status": "QUALITY_V1_INPUT_OR_EVIDENCE_UNAVAILABLE__HOLD",
            "private_ids_text_or_hashes_exported": False,
            "no_dataset_written": True, "quality_dataset_admitted": 0,
            "training_authorized": False, "expansion_allowed": False,
        }, sort_keys=True, indent=2))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
