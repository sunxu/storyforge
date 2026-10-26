#!/usr/bin/env python3
"""Read-only R55 Gold5 hard-rule subtype classification verifier (owner private).

All labels are supplemental, manually proposed annotations for existing AI-assisted
final category verdicts; they cannot certify correctness or alter original decisions.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys

SCHEMA = "storyforge-r55-gold5-hard-rule-subtype-diagnostic-v1"
SAFE_SCHEMA = "storyforge-r55-gold5-hard-rule-subtype-safe-v1"
SUBTYPES = (
    "player_psychology_or_intent", "player_action_or_speech",
    "user_event_continuity", "character_identity_or_relation",
    "world_timeline_age", "forbidden_phrase_exact",
    "forbidden_phrase_semantic", "forbidden_user_echo",
    "forbidden_echo_question", "dialogue_language_format",
)
VERDICTS = {"CONFIRMED", "REJECTED", "HOLD_INSUFFICIENT_EVIDENCE"}
ARMS = {"base", "gold", "v01", "v02", "v03"}
EXPECTED_HARD_C = 62
EXPECTED_HARD_H = 4
EXPECTED_RECORD_COUNT = 76

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def validate(docket, decisions, proposal, docket_sha, decisions_sha):
    if not __debug__:
        raise RuntimeError("refusing optimized Python -O mode; assertion-based validation must remain enabled")
    assert proposal.get("schema") == SCHEMA, "wrong schema"
    pins = proposal.get("source_sha256", {})
    assert pins.get("docket") == docket_sha and pins.get("decisions") == decisions_sha, "source pins differ"
    d_items, v_items = docket["items"], decisions["items"]
    assert len(d_items) == len(v_items) == EXPECTED_RECORD_COUNT, "source candidate count mismatch"
    toks = [x["candidate_token"] for x in d_items]
    assert len(set(toks)) == EXPECTED_RECORD_COUNT, "duplicate token"
    assert toks == [x["candidate_token"] for x in v_items], "source order/token mismatch"
    source_map = {x["candidate_token"]: x for x in d_items}
    decision_map = {x["candidate_token"]: x for x in v_items}
    confirmed, holds = set(), set()
    outcome_counts = Counter()
    for item in v_items:
        for category in ("agency", "hard_fact_or_ban"):
            verdict = item[category]["final_verdict"]
            assert verdict in VERDICTS, "invalid or empty final verdict"
            outcome_counts[verdict] += 1
            if category == "hard_fact_or_ban":
                key = item["candidate_token"]
                if verdict == "CONFIRMED": confirmed.add(key)
                elif verdict == "HOLD_INSUFFICIENT_EVIDENCE": holds.add(key)
    assert (len(confirmed), len(holds)) == (EXPECTED_HARD_C, EXPECTED_HARD_H)
    assert outcome_counts == {"CONFIRMED":79,"REJECTED":69,"HOLD_INSUFFICIENT_EVIDENCE":4}, "unexpected frozen final counts"
    r = proposal.get("confirmed_subtype_records")
    h = proposal.get("hold_evidence_records")
    assert isinstance(r,list) and isinstance(h,list)
    assert len(r) == EXPECTED_HARD_C and len(h) == EXPECTED_HARD_H, "incomplete annotation coverage"
    assert {x.get("candidate_token") for x in r} == confirmed, "confirmation token coverage mismatch"
    assert {x.get("candidate_token") for x in h} == holds, "HOLD token coverage mismatch"
    assert len({x["candidate_token"] for x in r}) == EXPECTED_HARD_C
    assert len({x["candidate_token"] for x in h}) == EXPECTED_HARD_H
    subtype_counts = Counter(); by_arm = defaultdict(Counter)
    hold_by_arm = Counter()
    for rec in r:
        token = rec["candidate_token"]
        original = source_map[token]
        verdict = decision_map[token]["hard_fact_or_ban"]
        arm = original["source_arm_PRIVATE"]
        subtype = rec["diagnostic_subtype"]
        assert arm in ARMS and rec["source_arm_PRIVATE"] == arm, "arm mismatch"
        assert rec["case_token_PRIVATE"] == original["case_token"], "case token mismatch"
        assert rec.get("category") == "hard_fact_or_ban"
        assert subtype in SUBTYPES, "unknown subtype"
        assert rec["original_final_verdict"] == "CONFIRMED"
        assert rec["legacy_issue_subtype"] == verdict["issue_subtype"]
        assert rec["candidate_quote"] == verdict["candidate_quote"], "candidate quote mismatch"
        assert rec["context_quote"] == verdict["context_quote"], "context quote mismatch"
        assert rec["rationale"] == verdict["rationale"], "rationale drift"
        # The source validator checks quote text exactness; here forbid relabeling without preserving it.
        assert rec["candidate_quote"].strip(), "missing candidate witness"
        assert rec["context_quote"].strip(), "missing context witness"
        subtype_counts[subtype] += 1; by_arm[arm][subtype] += 1
    assert set(subtype_counts) == set(SUBTYPES), "subtype coverage unexpectedly reduced"
    for rec in h:
        token=rec["candidate_token"]
        original=source_map[token]; verdict=decision_map[token]["hard_fact_or_ban"]
        assert rec["source_arm_PRIVATE"]==original["source_arm_PRIVATE"]
        hold_by_arm[original["source_arm_PRIVATE"]] += 1
        assert rec["case_token_PRIVATE"]==original["case_token"]
        assert rec["final_verdict"]=="HOLD_INSUFFICIENT_EVIDENCE"
        assert rec["original_evidence_gap"]==verdict["evidence_gap"]
        assert rec["original_rationale"]==verdict["rationale"]
        assert rec["next_action"] in ("RETAIN_HOLD_UNTIL_NEW_EVIDENCE",), "cannot autopromote HOLD"
    return {
        "schema":SAFE_SCHEMA,
        "status":"R55_GOLD5_RULE_SUBTYPES_DIAGNOSTIC_SAFE_PASS__NO_FINAL_RECLASSIFICATION__NO_R50",
        "source_frozen_docket_sha256":docket_sha,
        "source_frozen_decisions_sha256":decisions_sha,
        "source_selected_candidates":len(d_items),
        "source_category_judgments":len(d_items)*2,
        "source_final_verdict_counts":dict(sorted(outcome_counts.items())),
        "hard_fact_or_ban_confirmed_subtyped":len(confirmed),
        "hard_fact_or_ban_hold_unchanged":len(holds),
        "hold_by_arm":{a:hold_by_arm[a] for a in sorted(ARMS)},
        "subtype_counts":{k:subtype_counts[k] for k in SUBTYPES},
        "subtype_counts_by_arm":{a:{s:by_arm[a].get(s,0) for s in SUBTYPES} for a in sorted(ARMS)},
        "diagnostic_label_method":"AI-assisted read of first/second/third verdict rationale, candidate and rule quotes; primary mutually exclusive label; NOT independent semantic certification",
        "private_text_or_tokens_in_safe_receipt":False,
        "r50_accessed":False,
        "gpu_job_started":False,
        "training":False,
        "model_promoted":False,
        "owner_signoff":False,
        "original_final_verdicts_changed":False,
        "heldout_or_population_error_rate":False,
    }

def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument("--docket",required=True,type=Path)
    ap.add_argument("--decisions",required=True,type=Path)
    ap.add_argument("--subtypes",required=True,type=Path)
    ap.add_argument("--out",required=True,type=Path)
    args=ap.parse_args(argv)
    if args.out.exists(): ap.error("refusing to overwrite existing output")
    try:
        result=validate(load(args.docket),load(args.decisions),load(args.subtypes),digest(args.docket),digest(args.decisions))
    except (AssertionError,ValueError,KeyError,TypeError) as e:
        ap.error(f"FAIL_CLOSED: {e}")
    result["subtype_proposal_sha256"]=digest(args.subtypes)
    args.out.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    with args.out.open("x",encoding="utf-8") as f:
        json.dump(result,f,indent=2,sort_keys=True,ensure_ascii=False)
        f.write("\n")
    print(result["status"])
    print(f"SAFE_RECEIPT={args.out}")

if __name__=="__main__": main()
