"""R52 deduplicated R45 historical source exposure impact; private, no admission.

Replays frozen original R45 ZIP against seven authenticated R52 complete source
worlds and existing 537 historical witness records. Counts unique story UUIDs,
46 first-pass candidate exposure, and exact target SHA reuse separately.
No model-training exposure conclusion without actual R46 loader/job provenance.
No raw narrative/UUID/candidate text printed or committed to Git.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import stat
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

import v03_r52_historical_exposure_triage as prior
import v03_r52_reconcile_full21_world_graph as graph
import v03_r52_world_exact_isolation as identity

HOLD = "PENDING_NOT_APPROVED"
EXPECTED_ARCHIVE_SHA = "da4b7718f1c1cbd0429553b684eeaf70f207fd2e41aae4e8fe0a52a11b647b9e"
EXACT_SCREEN_STATUS = "R52_SEVEN_WORLD_HISTORICAL_EXPOSURE_SCREEN_COMPLETED__SEMANTIC_HOLD"
EXACT_GRAPH_STATUS = "R52_FULL_SOURCE_21_21_REVIEW_RECEIPTS_RECONCILED__GRAPH_HOLD"
WITNESS_COUNT = 537


def need(ok, code):
    if not ok:
        raise identity.GateHold(code)


def private_json(path: Path) -> dict:
    need(path.is_file() and not path.is_symlink() and
         stat.S_IMODE(path.stat().st_mode) == 0o600 and
         stat.S_IMODE(path.parent.stat().st_mode) & 0o077 == 0,
         "PRIVATE_JSON_NOT_SAFE")
    data = json.loads(path.read_text(encoding="utf8"))
    need(isinstance(data, dict), "PRIVATE_JSON_NOT_OBJECT")
    return data


def private_rows(path: Path, n: int) -> list[dict]:
    return identity.read_jsonl(path, private=True, count=n)


def validate_receipts(history: dict, graph_receipt: dict):
    need(history.get("schema") ==
         "storyforge-r52-historical-exposure-triage-safe-aggregate-v1" and
         history.get("status") == EXACT_SCREEN_STATUS and
         history.get("r45_original_archive_sha256") == EXPECTED_ARCHIVE_SHA and
         history.get("r45_private_49_15_included") is True and
         history.get("r45_original_archive_used_ephemerally") is True and
         history.get("long_text_candidate_witnesses") == WITNESS_COUNT and
         history.get("long_text_screen_kind_counts") == {
             "EXACT_LONG_MESSAGE": 273,
             "SAMPLED_120_CODEPOINT_FRAGMENT": 264
         } and
         history.get("exact_source_id_collision_rows_by_corpus") == {
             "r45_train": 29, "r45_validation": 13
         } and
         history.get("historic_cohorts_checked") == {
             "gold87": 87, "r45_train": 49, "r45_validation": 15,
             "v01_train": 65, "v01_validation": 15, "v01_test": 20
         } and
         history.get("first_pass_candidates") == 46 and
         history.get("source_messages_read") == 20577 and
         history.get("semantic_name_alias_or_paraphrase_isolation_verified") is False and
         history.get("source_exposure_owner_signed") is False and
         history.get("train_admitted") ==
         history.get("validation_admitted") ==
         history.get("training_split_assigned") ==
         history.get("world_components_signed") == 0 and
         history.get("r50_sealed_heldout_opened") is False,
         "R45_EXPOSURE_FROZEN_RECEIPT_CHANGED")
    need(graph_receipt.get("schema") ==
         "storyforge-r52-all21-world-graph-audit-safe-aggregate-v1" and
         graph_receipt.get("status") == EXACT_GRAPH_STATUS and
         graph_receipt.get("distinct_edges_reconciled") == 21 and
         graph_receipt.get("source_citations_reverified") == 87 and
         graph_receipt.get("first_pass_quality_possible") == 46 and
         graph_receipt.get("quality_hold") == 16 and
         graph_receipt.get("linked_world_component_owner_signatures") == 0 and
         graph_receipt.get("train_admitted") ==
         graph_receipt.get("validation_admitted") ==
         graph_receipt.get("training_split_allocated") == 0 and
         graph_receipt.get("r50_sealed_heldout_opened") is False,
         "WORLD_GRAPH21_PRIOR_RECEIPT_CHANGED")


def compute_impact(worlds: dict[int, dict],
                   cases: list[dict], owner_queue: list[dict],
                   cohorts: dict[str, list],
                   witnesses: list[dict]) -> tuple[list[dict], list[dict], dict]:
    need(set(cohorts) == {"r45_train", "r45_validation"} and
         len(cohorts["r45_train"]) == 49 and
         len(cohorts["r45_validation"]) == 15 and
         len(worlds) == 7 and len(cases) == 46 and len(owner_queue) == 7 and
         len(witnesses) == WITNESS_COUNT,
         "R45_SOURCE_OR_R52_INPUT_CARDINALITY_DRIFT")
    source_ids = {w["source_story_id"]: r for r, w in worlds.items()}
    need(len(source_ids) == 7 and len({
        row["source_story_id"] for row in owner_queue
    }) == 7 and set(source_ids) == {
        row["source_story_id"] for row in owner_queue
    }, "R52_WORLD_OWNER_SOURCE_SET_CHANGED")
    owner_by_rank = {r["story_rank"]: r for r in owner_queue}
    need(len(owner_by_rank) == 7 and set(owner_by_rank) == set(worlds) and
         all(r["training_admission"] == HOLD and
             r.get("world_split") is None and
             r.get("final_component_isolation") == "NOT_VERIFIED" and
             r.get("full_story_alias_review_owner_signed") is False
             for r in owner_queue),
         "R52_WORLD_OWNER_SIGNOFF_PREMATURE")
    histories = defaultdict(lambda: defaultdict(list))
    historical_target_shas = defaultdict(lambda: defaultdict(set))
    missing_target_markers = Counter()
    for split, cohort in cohorts.items():
        for row_ordinal, row in enumerate(cohort):
            sid, messages = prior.get_historical_messages(row, split)
            if sid not in source_ids:
                continue
            rank = source_ids[sid]
            histories[rank][split].append(row_ordinal)
            final = messages[-1] if messages else None
            if (isinstance(final, dict) and
                final.get("role", "").strip().lower() == "assistant" and
                isinstance(final.get("content"), str) and
                final["content"]):
                historical_target_shas[rank][split].add(
                    prior.sha_bytes(final["content"].encode("utf8")))
            else:
                missing_target_markers[split] += 1
    need(sum(len(h["r45_train"]) for h in histories.values()) == 29 and
         sum(len(h["r45_validation"]) for h in histories.values()) == 13,
         "R45_UUID_OVERLAP_RECOUNT_DIFFERENT")
    selected = defaultdict(list)
    case_ids = set()
    for row in cases:
        rank = row.get("story_rank")
        sid = row.get("source_story_id")
        cid = row.get("candidate_id")
        sha = row.get("target_sha256")
        need(type(rank) is int and rank in worlds and
             sid == worlds[rank]["source_story_id"] and
             isinstance(cid, str) and cid not in case_ids and
             isinstance(sha, str) and len(sha) == 64 and
             row.get("training_admission") == HOLD and
             row.get("split") is None and
             row.get("eligibility_stage") ==
             "QUALITY_POSSIBLE__NEEDS_GATES" and
             row.get("final_quality_and_safety_signoff") == "PENDING",
             "R52_46_FROZEN_POSITIVE_CASE_CHANGED")
        case_ids.add(cid)
        selected[rank].append(row)
    need(sum(len(x) for x in selected.values()) == 46 and
         all(owner_by_rank[r]["quality_first_pass_possible"] ==
             len(selected[r]) for r in worlds),
         "R52_WORLD_OWNER_FIRST_PASS_COUNT_CHANGED")
    by_world_witness = defaultdict(list)
    unique_witnesses = set()
    unique_pair_refs = set()
    for item in witnesses:
        rank = item.get("source_rank")
        kind = item.get("match_kind")
        split = item.get("historical_corpus")
        idx = item.get("original_source_array_index")
        historic_i = item.get("historical_record_ordinal")
        historic_msg_i = item.get("historical_message_index")
        need(rank in worlds and
             item.get("source_story_id") == worlds[rank]["source_story_id"] and
             split in cohorts and
             kind in ("EXACT_LONG_MESSAGE", "SAMPLED_120_CODEPOINT_FRAGMENT") and
             type(idx) is int and
             0 <= idx < len(worlds[rank]["original_root_messages"]) and
             worlds[rank]["original_root_messages"][idx]["source_body_sha256"] ==
             item.get("source_body_sha256") and
             type(historic_i) is int and 0 <= historic_i < len(cohorts[split]) and
             type(historic_msg_i) is int and
             item.get("training_admission") == HOLD,
             "WITNESS_ID_SHA_OR_SOURCE_CHANGED")
        sid, old_msgs = prior.get_historical_messages(
            cohorts[split][historic_i], split)
        need(0 <= historic_msg_i < len(old_msgs) and
             prior.sha_bytes(old_msgs[historic_msg_i]["content"].encode("utf8")) ==
             item.get("historical_message_sha256"),
             "R45_WITNESS_HISTORICAL_MESSAGE_HASH_CHANGED")
        fingerprint = (rank, idx, split, historic_i, historic_msg_i, kind)
        need(fingerprint not in unique_witnesses, "WITNESS_DUPLICATE_EXACT_ROW")
        unique_witnesses.add(fingerprint)
        unique_pair_refs.add((rank, idx, split, historic_i, historic_msg_i))
        by_world_witness[rank].append(item)
    risk_rows = []
    decision_rows = []
    case_count_by_class = Counter()
    exact_target_by_split = Counter()
    worlds_by_class = Counter()
    for rank, world in sorted(worlds.items()):
        train_ord = histories[rank]["r45_train"]
        val_ord = histories[rank]["r45_validation"]
        if train_ord:
            group = "R45_TRAIN_UUID_OVERLAP__MODEL_LINEAGE_HOLD"
        elif val_ord:
            group = "R45_VALIDATION_UUID_OVERLAP__EVALUATION_LINEAGE_HOLD"
        else:
            group = "NO_R45_UUID_OVERLAP_OBSERVED__SEMANTIC_HOLD"
        worlds_by_class[group] += 1
        ww = by_world_witness[rank]
        unique_old = len({
            (w["historical_corpus"], w["historical_record_ordinal"],
             w["historical_message_index"]) for w in ww
        })
        unique_new = len({
            w["original_source_array_index"] for w in ww
        })
        risk_rows.append({
            "schema": "storyforge-r52-private-r45-world-impact-v1",
            "private_do_not_commit": True,
            "story_rank": rank,
            "source_story_id": world["source_story_id"],
            "r45_train_row_ordinals": train_ord,
            "r45_validation_row_ordinals": val_ord,
            "r45_train_uuid_overlap": bool(train_ord),
            "r45_validation_uuid_overlap": bool(val_ord),
            "r45_train_direct_target_coverage_unverified": (
                missing_target_markers["r45_train"] > 0),
            "r45_validation_direct_target_coverage_unverified": (
                missing_target_markers["r45_validation"] > 0),
            "original_source_text_witness_records": len(ww),
            "unique_original_message_indices_with_text_hit": unique_new,
            "unique_historical_messages_with_text_hit": unique_old,
            "r52_preliminary_quality_cases": len(selected[rank]),
            "conservative_evaluation_risk": group,
            "actual_trained_model_weights_exposure_proved": False,
            "world_component_certified": False,
            "training_admission": HOLD,
        })
        for row in selected[rank]:
            match_train = row["target_sha256"] in historical_target_shas[rank]["r45_train"]
            match_val = row["target_sha256"] in historical_target_shas[rank]["r45_validation"]
            case_count_by_class[group] += 1
            exact_target_by_split["r45_train"] += int(match_train)
            exact_target_by_split["r45_validation"] += int(match_val)
            decision_rows.append({
                "schema": "storyforge-r52-private-r45-case-exposure-v1",
                "private_do_not_commit": True,
                "candidate_id": row["candidate_id"],
                "story_rank": rank,
                "source_story_id": world["source_story_id"],
                "target_sha256": row["target_sha256"],
                "r45_train_story_uuid_overlap": bool(train_ord),
                "r45_validation_story_uuid_overlap": bool(val_ord),
                "exact_original_target_sha_in_r45_train": match_train,
                "exact_original_target_sha_in_r45_validation": match_val,
                "world_level_risk_route": group,
                "model_training_exposure_confirmed": False,
                "final_quality_safety_signoff": "PENDING",
                "world_component_certified": False,
                "split": None,
                "training_admission": HOLD,
            })
    need(len(decision_rows) == 46 and sum(worlds_by_class.values()) == 7 and
         len(unique_witnesses) == 537, "R45_WORLD_OR_TARGET_IMPACT_COUNTS_CHANGED")
    safe = {
        "schema": "storyforge-r52-r45-world-impact-safe-aggregate-v1",
        "status": "R52_R45_HISTORICAL_WORLD_IMPACT_RECONCILED__SEMANTIC_AND_MODEL_LINEAGE_HOLD",
        "r45_train_story_id_collision_rows": 29,
        "r45_validation_story_id_collision_rows": 13,
        "distinct_r52_worlds_with_r45_train_uuid_overlap":
            sum(bool(h["r45_train"]) for h in histories.values()),
        "distinct_r52_worlds_with_r45_validation_uuid_overlap":
            sum(bool(h["r45_validation"]) for h in histories.values()),
        "distinct_r52_worlds_with_both_r45_splits_uuid_overlap":
            sum(bool(h["r45_train"]) and bool(h["r45_validation"])
                for h in histories.values()),
        "distinct_r52_worlds_with_any_r45_uuid_overlap":
            sum(bool(h["r45_train"]) or bool(h["r45_validation"])
                for h in histories.values()),
        "r52_world_risk_route_counts": dict(sorted(worlds_by_class.items())),
        "r52_46_first_pass_case_risk_route_counts": dict(sorted(case_count_by_class.items())),
        "first_pass_target_sha_exact_matches": dict(sorted(exact_target_by_split.items())),
        "r45_rows_with_unusable_last_assistant_target_marker": dict(sorted(missing_target_markers.items())),
        "all_original_source_text_witnesses_reverified": len(witnesses),
        "unique_message_pair_witnesses_ignoring_match_kind": len(unique_pair_refs),
        "unique_r52_original_source_messages_with_text_hit": sum(
            r["unique_original_message_indices_with_text_hit"] for r in risk_rows),
        "full_available_world_source_messages": 20577,
        "r45_original_archive_sha256": EXPECTED_ARCHIVE_SHA,
        "first_pass_candidates": 46,
        "seven_world_signatures": 0,
        "train_admitted": 0,
        "validation_admitted": 0,
        "split_assigned": 0,
        "actual_r46_model_training_exposure_verified": False,
        "gold87_v01_semantic_aliases_cleared": False,
        "r50_sealed_heldout_opened": False,
        "private_story_uuid_candidate_names_or_text_in_stdout": False,
    }
    return risk_rows, decision_rows, safe


def run(owner_source: Path, r45_original: Path, history_dir: Path,
        graph_dir: Path, post_quality_dir: Path):
    history = private_json(history_dir / "R52_HISTORICAL_EXPOSURE_SAFE_AGGREGATE.json")
    graph_receipt = private_json(
        graph_dir / "R52_ALL_21_WORLD_GRAPH_SAFE_AGGREGATE.json")
    validate_receipts(history, graph_receipt)
    need(r45_original.is_file() and not r45_original.is_symlink() and
         prior.exact.sha_file(r45_original) == EXPECTED_ARCHIVE_SHA,
         "R45_ORIGINAL_ZIP_HASH_CHANGED")
    worlds, _ = graph.recover_worlds(owner_source)
    witnesses = private_rows(
        history_dir / "R52_PRIVATE_HISTORICAL_EXPOSURE_WITNESSES.jsonl",
        WITNESS_COUNT)
    cases = private_rows(
        post_quality_dir / "R52_PRIVATE_FIRST_PASS_46_SHORTLIST.jsonl", 46)
    queue = private_rows(
        graph_dir / "R52_PRIVATE_07_WORLD_GRAPH_OWNER_SIGNOFF_QUEUE.jsonl", 7)
    with tempfile.TemporaryDirectory(prefix="r52-impact-r45-") as temp:
        folder = Path(temp)
        folder.chmod(0o700)
        a, b = prior.extract_verified_r45_archive(r45_original, folder)
        cohorts = {
            "r45_train": list(prior.exact.read_jsonl(a, private=True, count=49)),
            "r45_validation": list(prior.exact.read_jsonl(b, private=True, count=15))
        }
        expected_witnesses, counts, collisions = prior.triage(worlds, cohorts)
        need(expected_witnesses == witnesses and
             dict(collisions) == {"r45_train": 29, "r45_validation": 13} and
             counts["EXACT_LONG_MESSAGE"] == 273 and
             counts["SAMPLED_120_CODEPOINT_FRAGMENT"] == 264,
             "R45_PRIOR_WITNESS_REPLAY_MISMATCH")
        return compute_impact(worlds, cases, queue, cohorts, witnesses)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-zip", type=Path, required=True)
    parser.add_argument("--r45-original-zip", type=Path, required=True)
    parser.add_argument("--history-dir", type=Path, required=True)
    parser.add_argument("--graph21-dir", type=Path, required=True)
    parser.add_argument("--post-quality-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        out = args.out_dir.expanduser().absolute()
        need(out.is_dir() and not out.is_symlink() and
             stat.S_IMODE(out.stat().st_mode) & 0o077 == 0,
             "OUTPUT_DIRECTORY_NOT_PRIVATE")
        world, cases, safe = run(
            args.source_zip.expanduser().absolute(),
            args.r45_original_zip.expanduser().absolute(),
            args.history_dir.expanduser().absolute(),
            args.graph21_dir.expanduser().absolute(),
            args.post_quality_dir.expanduser().absolute())
        outputs = {
            "R52_PRIVATE_07_R45_WORLD_EXPOSURE_IMPACT.jsonl": world,
            "R52_PRIVATE_46_R45_CASE_EXPOSURE_IMPACT.jsonl": cases,
        }
        files = {}
        for name, value in outputs.items():
            files[out / name] = "".join(
                json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n"
                for row in value)
        files[out / "R52_R45_WORLD_EXPOSURE_IMPACT_SAFE_AGGREGATE.json"] = (
            json.dumps(safe, sort_keys=True, indent=2, ensure_ascii=False) + "\n")
        need(all(not x.exists() and not x.is_symlink() for x in files),
             "OUTPUT_ALREADY_EXISTS")
        old = os.umask(0o077)
        try:
            for path, text in files.items():
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "w", encoding="utf8") as output:
                    output.write(text)
        finally:
            os.umask(old)
    except (OSError, TypeError, KeyError, ValueError,
            json.JSONDecodeError) as exc:
        marker = str(exc) if isinstance(exc, identity.GateHold) else type(exc).__name__
        print("R52_R45_IMPACT_HOLD__" + marker, file=sys.stderr)
        return 2
    print(safe["status"])
    print(json.dumps(safe, sort_keys=True, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
