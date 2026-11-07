"""R60 P2 read-only private evidence backlog; never admits or upgrades a Case."""
from __future__ import annotations

import argparse
import json
import re
import stat
import sys
from collections import Counter
from pathlib import Path

from experiments.r58_quality import r60_gold192_canonical_a_v3 as canon
from experiments.r58_quality import r60_gold192_supabase_extract_v3 as source
from experiments.r58_quality import r60_p1_case_triage as p1

SCHEMA = "storyforge_r60_p2_evidence_gap_safe_v1"
STAGE_SCHEMA = "storyforge-quality-v1-source-staging-private-v1"
STAGE_READY = "SOURCE_CONTEXT_STAGED__QUALITY_REVIEW_PENDING"
SCORES = ("chinese_prose", "character_consistency", "npc_initiative",
          "player_agency", "rule_fidelity", "narrative_continuity")
FLOORS = {"chinese_prose": 4, "character_consistency": 4,
          "npc_initiative": 3, "player_agency": 4, "rule_fidelity": 4,
          "narrative_continuity": 4}


def validated_stage(stage_raw: bytes, safe_raw: bytes) -> set[str]:
    # Stage is optional, but if supplied its receipt must be verified.
    from experiments.r58_quality.r59_staging_receipt import valid_staging_receipt

    receipt = json.loads(safe_raw)
    if not valid_staging_receipt(receipt, p1.digest(stage_raw)):
        raise p1.Hold("STAGE_RECEIPT_PIN_INVALID")
    rows = p1.jsonl(stage_raw)
    ids = set()
    for row in rows:
        if row.get("schema") != STAGE_SCHEMA:
            raise p1.Hold("STAGE_SCHEMA_INVALID")
        if row.get("status") != STAGE_READY:
            continue
        case_id = row.get("case_id")
        if not isinstance(case_id, str) or not case_id or case_id in ids:
            raise p1.Hold("STAGE_READY_DUPLICATE_INVALID")
        ids.add(case_id)
    return ids


def build(raw: dict[str, bytes], stage: set[str] | None = None,
          limit: int = 16) -> tuple[list[dict], dict]:
    if not 1 <= limit <= 28:
        raise p1.Hold("LIMIT_INVALID")
    # Re-verify the complete frozen P1 inputs, not just an untrusted P1 output.
    p1_rows, p1_safe = p1.triage(raw, source, canon)
    a = json.loads(raw["reviewer_a"])
    canon.validate_reviewer_a_v3(a)
    a_by_id = {r["case_id"]: r for r in a["records"]}
    indexed = {r["case_id"]: r for r in p1_rows}
    slots = p1.jsonl(raw["evidence_slots"])
    slot_by_id = {r["case_id"]: r for r in slots}
    if stage is not None and not stage.issubset(indexed):
        raise p1.Hold("STAGE_CASE_OUTSIDE_FROZEN_SET")
    chosen = [r for r in p1_rows if r["explicit_ab_selected"]]
    if len(chosen) != 28:
        raise p1.Hold("P1_CANDIDATE_COUNT_DRIFT")
    queue = []
    for row in chosen:
        case_id = row["case_id"]
        a_row = a_by_id[case_id]
        scores = a_row["scores_1_to_5"]
        if (not canon.scores_valid(scores)
                or a_row["case_level_scored_review_present"] is not True):
            raise p1.Hold("REVIEWER_A_SCORING_INVALID")
        slot = slot_by_id[case_id]
        if slot.get("input_evidence_class") != "UNKNOWN_NOT_REVIEWED":
            raise p1.Hold("EVIDENCE_SLOTS_STATE_DRIFT")
        floor_pass = all(scores[k] >= FLOORS[k] for k in SCORES)
        stage_ready = None if stage is None else case_id in stage
        gaps = ["SENT_MODEL_INPUT_NOT_REVIEWED",
                "REQUEST_ATTEMPT_LINK_NOT_VERIFIED",
                "OWNER_EVIDENCE_NOT_VERIFIED",
                "PROTECTED_WORLD_EXPOSURE_NOT_VERIFIED"]
        if not floor_pass:
            gaps.insert(0, "REVIEWER_A_QUALITY_BELOW_FLOOR")
        if stage is None:
            gaps.append("OLD_STRICT_STAGE_NOT_CROSSCHECKED")
        elif not stage_ready:
            gaps.append("OLD_STRICT_STAGE_NOT_READY")
        queue.append({
            "case_id": case_id,
            "target_sha256": row["target_sha256"],
            "old_strict_stage_ready": stage_ready,
            "reviewer_a_scores_frozen": scores,
            "reviewer_a_floor_pass": floor_pass,
            "priority_source_rank": row["priority_rank"],
            "input_evidence_class": "UNKNOWN_NOT_REVIEWED",
            "missing_evidence_codes": gaps,
            "owner_complete": False,
            "binder_bound": False,
            "quality_v1_admitted": False,
        })
    queue.sort(key=lambda r: (
        0 if r["old_strict_stage_ready"] is True else 1,
        0 if r["reviewer_a_floor_pass"] else 1,
        -sum(r["reviewer_a_scores_frozen"].values()),
        r["priority_source_rank"],
    ))
    for n, row in enumerate(queue, start=1):
        row["p2_priority_rank"] = n
        row["selected_for_first_pass"] = n <= limit
    counts = Counter(code for r in queue[:limit] for code in r["missing_evidence_codes"])
    safe = {
        "schema": SCHEMA, "status": "P2_PRIORITIZED_EVIDENCE_GAPS__NO_CLASSIFICATION_PROMOTION",
        "gold192_total": 192, "explicit_ab_candidates": len(queue),
        "queue_first_pass_count": min(limit, len(queue)),
        "candidate_a_scores_meet_v1_floors": sum(r["reviewer_a_floor_pass"] for r in queue),
        "old_strict_ready_crosscheck": "VERIFIED_STAGING_RECEIPT" if stage is not None else "NOT_CHECKED",
        "old_strict_ready_total": len(stage) if stage is not None else None,
        "old_strict_ready_intersection_ab": sum(r["old_strict_stage_ready"] is True for r in queue) if stage is not None else None,
        "first_pass_missing_evidence_counts": dict(sorted(counts.items())),
        "input_evidence_class_counts": p1_safe["input_evidence_class_counts"],
        "request_attempt_linkage_verified_count": 0,
        "exact_sent_payload_verified_count": 0,
        "owner_complete": 0, "binder_bound": 0, "quality_v1_admitted": 0,
        "dataset_frozen": False, "cpu_tokenizer_collator_pass": False,
        "training_authorized": False, "gpu_started": False,
        "database_modified": False, "r50_accessed": False,
        "private_values_emitted": False,
    }
    return queue, safe


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("reviewer-a", "reviewer-b", "exclusions", "source-packets",
                 "source-locators", "source-safe", "evidence-slots", "output-dir"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--staged-jsonl", type=Path)
    parser.add_argument("--staging-safe", type=Path)
    parser.add_argument("--first-pass", type=int, default=16)
    args = parser.parse_args()
    try:
        if (args.staged_jsonl is None) != (args.staging_safe is None):
            raise p1.Hold("STAGE_AND_RECEIPT_MUST_BE_PAIRED")
        keys = ("reviewer_a", "reviewer_b", "exclusions", "source_packets",
                "source_locators", "source_safe", "evidence_slots")
        raw = {key: p1.read_private(getattr(args, key)) for key in keys}
        stage = None
        if args.staged_jsonl:
            stage = validated_stage(p1.read_private(args.staged_jsonl),
                                    p1.read_private(args.staging_safe))
        out = args.output_dir
        if (not out.is_absolute() or out.exists() or out.is_symlink()
                or not out.parent.is_dir() or out.parent.is_symlink()
                or stat.S_IMODE(out.parent.stat().st_mode) != 0o700
                or out.resolve().is_relative_to(Path(__file__).resolve().parents[2])):
            raise p1.Hold("PRIVATE_OUTPUT_DIR_INVALID")
        queue, safe = build(raw, stage, args.first_pass)
        out.mkdir(mode=0o700)
        p1.save_new(out / "R60_P2_PRIORITY_PRIVATE.jsonl", queue, lines=True)
        p1.save_new(out / "R60_P2_SAFE.json", safe)
        print(json.dumps(safe, ensure_ascii=False, sort_keys=True))
        return 0
    except (p1.Hold, ValueError, TypeError, KeyError, OSError, ImportError) as exc:
        code = str(exc) if isinstance(exc, p1.Hold) and re.fullmatch(r"[A-Z0-9_]{1,80}", str(exc)) else "P2_VALIDATION_FAILED"
        print(json.dumps({
            "schema": SCHEMA, "status": "P2_HOLD", "reason_code": code,
            "quality_v1_admitted": 0, "gpu_started": False,
            "r50_accessed": False, "database_modified": False,
            "private_values_emitted": False,
        }), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
