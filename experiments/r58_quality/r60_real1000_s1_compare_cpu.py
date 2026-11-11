"""S1 Owner-only Claude/Codex blinded crosswalk and comparison.

No network, model inference or training decisions. Only aggregate SAFE to stdout.
Create-only private comparison contains positions and both model opinions, no prose.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import r60_real1000_s0_audit_cpu as s0
import r60_real1000_s1_blind20_prepare_cpu as blind
import r60_real1000_pilot20_local_review as pilot
import r60_real_ai_dual_review as reviewer
import r60_real_private_batch as private

SCHEMA = "storyforge_r60_real1000_s1_codex_claude_compare_safe_v1"
PRIVATE_SCHEMA = "storyforge_r60_real1000_s1_codex_claude_compare_private_v1"
PRIVATE_FILENAME = "R60_S1_CODEX_CLAUDE_COMPARE_PRIVATE.json"
CODEX_SCHEMA = "storyforge_r60_s1_codex20_advisory_v1"
RAW_FILENAME = "R60_S1_CODEX20_RAW_PRIVATE.json"
MAX_BYTES = 150000


class Hold(ValueError):
    pass


def compare(sample_dir: Path, review_dir: Path, blind_dir: Path,
            owner_dir: Path, codex_path: Path) -> tuple[dict, dict]:
    """Require exact original input binding, 20 rubric-valid Codex reviews."""
    safe, ledger = s0.audit(sample_dir, review_dir)
    if safe["pilot20_processed"] != 20:
        raise Hold("S0_NOT_COMPLETE_HOLD")
    expected_safe, expected_blind, expected_map = blind.prepare(
        sample_dir, review_dir)
    if expected_safe["cases_prepared"] != 20:
        raise Hold("S1_BLIND_NOT_READY_HOLD")
    private.private_dir(blind_dir, create=False)
    private.private_dir(owner_dir, create=False)
    blind_doc = json.loads(private.read_private(
        blind_dir / blind.BLIND_FILENAME, MAX_BYTES))
    owner_map = json.loads(private.read_private(
        owner_dir / blind.CROSSWALK_FILENAME, MAX_BYTES))
    if blind_doc != expected_blind or owner_map != expected_map:
        raise Hold("S1_FROZEN_INPUT_OR_MAP_MISMATCH_HOLD")
    if owner_map["blind_input_sha256"] != pilot.sha(
            pilot.canonical(blind_doc)):
        raise Hold("BLIND_INPUT_SHA_HOLD")

    codex = json.loads(private.read_private(codex_path, MAX_BYTES))
    if (not isinstance(codex, dict)
            or set(codex) != {"schema", "reviews"}
            or codex["schema"] != CODEX_SCHEMA
            or not isinstance(codex["reviews"], list)
            or len(codex["reviews"]) != 20):
        raise Hold("CODEX_SCHEMA_HOLD")
    codex_by_id = {}
    for record in codex["reviews"]:
        if not isinstance(record, dict) or set(record) != {
                "blind_id", "decision", "scores", "severe_flags", "reason_cn"}:
            raise Hold("CODEX_REVIEW_SCHEMA_HOLD")
        blind_id = record["blind_id"]
        if (type(blind_id) is not str or blind_id in codex_by_id
                or blind_id not in {f"B{i:03d}" for i in range(1, 21)}):
            raise Hold("CODEX_ID_HOLD")
        reviewer.parse_model_response({
            name: record[name] for name in
            ("decision", "scores", "severe_flags", "reason_cn")
        })
        codex_by_id[blind_id] = record

    entries = []
    matrix = Counter()
    codex_decisions = Counter()
    claude_decisions = Counter()
    codex_severe = Counter()
    exact_agreement = 0
    flags_disagreement = 0
    for mapping in owner_map["entries"]:
        blind_id = mapping["blind_id"]
        position = mapping["pilot_position"]
        if not 1 <= position <= 20:
            raise Hold("POSITION_HOLD")
        c = codex_by_id[blind_id]
        a = ledger["rows"][position - 1]
        case = next(x for x in blind_doc["cases"] if x["blind_id"] == blind_id)
        payload = {
            "history_messages": case["history_messages"],
            "assistant_target": case["assistant_target"],
        }
        if mapping["case_payload_sha256"] != pilot.sha(pilot.canonical(payload)):
            raise Hold("CASE_PAYLOAD_BINDING_HOLD")
        cd = c["decision"]
        ad = a["original_model_decision"]
        kind = a["review_kind"]
        if kind == "VALID_ADVISORY":
            claude_decisions[ad] += 1
            matrix[(ad, cd)] += 1
            if ad == cd:
                exact_agreement += 1
        else:
            pass  # Original Claude PASS failed the frozen threshold.
        if c["severe_flags"] != a["severe_flags"]:
            flags_disagreement += 1
        codex_decisions[cd] += 1
        codex_severe.update({
            k: 1 for k, value in c["severe_flags"].items() if value
        })
        entries.append({
            "blind_id": blind_id,
            "pilot_position": position,
            "claude_review_kind": kind,
            "claude_decision_raw": ad,
            "codex_decision": cd,
            "claude_scores": a["scores"],
            "codex_scores": c["scores"],
            "claude_severe_flags": a["severe_flags"],
            "codex_severe_flags": c["severe_flags"],
            "decision_disagreement": ad != cd or kind != "VALID_ADVISORY",
            "severe_flag_disagreement": c["severe_flags"] != a["severe_flags"],
            "owner_adjudication": "NOT_ADJUDICATED",
        })
    if len(entries) != 20 or len({x["pilot_position"] for x in entries}) != 20:
        raise Hold("CROSSWALK_DUPLICATE_HOLD")
    if sum(codex_decisions.values()) != 20:
        raise Hold("CODEX_COUNT_HOLD")
    report = {
        "schema": SCHEMA,
        "status": "S1_CODEX_CLAUDE_COMPARE_PASS__OWNER_ADJUDICATION_PENDING",
        "cases": 20,
        "claude_valid_advisory": 18,
        "claude_quality_conflicts": 2,
        "claude_model_decisions": {
            k: claude_decisions[k] for k in ("PASS", "HOLD", "REJECT")},
        "codex_model_decisions": {
            k: codex_decisions[k] for k in ("PASS", "HOLD", "REJECT")},
        "agreement_on_18_valid_claude": exact_agreement,
        "disagreement_on_18_valid_claude": 18 - exact_agreement,
        "severe_flag_disagreements_all20": flags_disagreement,
        "decision_cross_tab_valid_claude": {
            a: {c: matrix[(a, c)] for c in ("PASS", "HOLD", "REJECT")}
            for a in ("PASS", "HOLD", "REJECT")
        },
        "codex_severe_flag_counts": {
            k: codex_severe[k] for k in private.SEVERE},
        "independent_ai_reviews": 20,
        "owner_final_adjudications": 0,
        "quality_v1_admitted": 0,
        "train_admitted": 0,
        "model_inference_calls": 0,
        "database_accessed": False,
        "gpu_job_started": False,
        "private_values_emitted": False,
    }
    result = {
        "schema": PRIVATE_SCHEMA,
        "status": "S1_COMPARISON_ADVISORY_ONLY__NO_OWNER_ADJUDICATION",
        "blind_input_sha256": owner_map["blind_input_sha256"],
        "codex_result_sha256": pilot.sha(private.read_private(
            codex_path, MAX_BYTES)),
        "rows": sorted(entries, key=lambda x: x["pilot_position"]),
        "quality_v1_admitted": 0,
        "train_admitted": 0,
    }
    return report, result


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--sample-dir", type=Path, required=True)
    p.add_argument("--review-dir", type=Path, required=True)
    p.add_argument("--blind-dir", type=Path, required=True)
    p.add_argument("--owner-map-dir", type=Path, required=True)
    p.add_argument("--codex-result", type=Path, required=True)
    p.add_argument("--private-report-dir", type=Path)
    args = p.parse_args()
    try:
        safe, result = compare(
            args.sample_dir, args.review_dir, args.blind_dir,
            args.owner_map_dir, args.codex_result)
        if args.private_report_dir is not None:
            if (args.private_report_dir.exists()
                    or args.private_report_dir.is_symlink()):
                raise Hold("REPORT_ALREADY_EXISTS_HOLD")
            private.private_dir(args.private_report_dir, create=True)
            private.write_new(
                args.private_report_dir / PRIVATE_FILENAME,
                pilot.canonical(result))
            safe["private_comparison_written"] = True
        else:
            safe["private_comparison_written"] = False
        print(json.dumps(safe, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - redact source/private errors
        code = str(exc) if isinstance(exc, Hold) else "S1_COMPARE_INPUT_HOLD"
        print(json.dumps({
            "schema": SCHEMA,
            "status": "S1_CODEX_CLAUDE_COMPARE_HOLD",
            "reason_code": code,
            "model_inference_calls": 0,
            "database_accessed": False,
            "gpu_job_started": False,
            "private_values_emitted": False,
            "quality_v1_admitted": 0,
            "train_admitted": 0,
        }, sort_keys=True), file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
