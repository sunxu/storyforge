"""Synthetic-only crosswalk tests, no remote API or private story data."""
from __future__ import annotations

import json

import pytest
import r60_real1000_v123_crosswalk as crosswalk
import r60_real_private_batch as private


def case(i):
    return {
        "case_key": f"case-{i}",
        "assistant_target_sha256": f"target-{i}",
        "history_messages_sha256": f"history-{i}",
    }


def answer(decision):
    flags = {k: False for k in private.SEVERE}
    if decision == "REJECT":
        flags["hard_fact_or_ban"] = True
    return {
        "decision": decision, "scores": dict(private.FLOORS),
        "severe_flags": flags, "reason_cn": "合成审核结论",
    }


def review(side, decision):
    return {"reviewer_key": f"ai-model-{side}", **answer(decision)}


def original(i, reviews):
    return {
        "position": i, "case_key": f"case-{i}",
        "assistant_target_sha256": f"target-{i}",
        "history_messages_sha256": f"history-{i}",
        "receipt_sha256": f"v1-hash-{i}", "reviews": reviews,
    }


def slot(position, side):
    return {"position": position, "missing_slots": [{"side": side}]}


def replay(position, side, decision, *, version):
    return {
        "position": position, "side": side,
        "status": f"{version}_{decision}" if decision else "TECHNICAL_HOLD",
        "result": answer(decision) if decision else None,
        "receipt_sha256": f"{version}-hash-{position}",
        "v1_receipt_sha256": f"v1-hash-{position}",
    }


def test_merges_only_missing_review_slots(monkeypatch):
    monkeypatch.setattr(crosswalk, "_valid_decision",
                        crosswalk._valid_decision)
    cases = [case(i) for i in range(1, 5)]
    v1 = [
        original(1, [review("a", "PASS"), review("b", "PASS")]),
        original(2, [review("a", "PASS")]),
        original(3, [review("b", "PASS")]),
        original(4, [review("a", "REJECT")]),
    ]
    v2 = [replay(2, "b", "PASS", version="V2"),
          replay(3, "a", None, version="V2"),
          replay(4, "b", "PASS", version="V2")]
    selected = [slot(2, "b"), slot(3, "a"), slot(4, "b")]
    v3 = [replay(3, "a", "PASS", version="V3")]
    queue = [{"position": 3, "side": "a"}]
    # Fixed expected batch width only for synthetic fixture.
    real_len = len
    # Provide 1000 rows with non-pass zero-review synthetic padding.
    for i in range(5, 1001):
        cases.append(case(i))
        v1.append(original(i, []))
    # V2 original design always selected exactly 237 single-pass slots.
    for i in range(5, 239):
        selected.append(slot(i, "b"))
    for item in selected[3:]:
        if item["position"] <= 4:
            continue
        # pad all remaining V2 slots as not-yet-attempted
    result = crosswalk._apply(cases, v1, v2, v3, selected, queue)
    assert result["candidate_count"] == 3
    assert result["outcome_counts"]["dual_pass_candidate"] == 3
    assert result["outcome_counts"]["two_valid_not_dual_pass"] == 1
    assert result["outcome_counts"]["neither_valid"] == 996
    assert result["gold_promoted"] is False
    assert result["train_admitted"] == 0
    assert len(result["entries"]) == 3
    assert real_len(result["entries"]) == 3


def test_cannot_replace_prior_success():
    cases = [case(i) for i in range(1, 1001)]
    v1 = [original(i, []) for i in range(1, 1001)]
    v1[0] = original(1, [review("a", "PASS"), review("b", "PASS")])
    selected = [slot(i, "a") for i in range(2, 239)]
    with pytest.raises(crosswalk.Hold, match="V2_OVERWRITES_V1_HOLD"):
        crosswalk._apply(
            cases, v1, [replay(1, "a", "PASS", version="V2")],
            [], [slot(1, "a")] + selected[:236], [])


def test_v3_may_not_override_valid_v2():
    cases = [case(i) for i in range(1, 1001)]
    v1 = [original(i, []) for i in range(1, 1001)]
    selected = [slot(i, "a") for i in range(2, 239)]
    v2 = [replay(2, "a", "PASS", version="V2")]
    v3 = [replay(2, "a", "PASS", version="V3")]
    with pytest.raises(
            crosswalk.Hold, match="V3_OVERWRITES_EARLIER_VALID_REVIEW_HOLD"):
        crosswalk._apply(cases, v1, v2, v3, selected,
                         [{"position": 2, "side": "a"}])


def test_review_scores_cannot_be_laundered():
    bad = review("a", "PASS")
    bad["scores"]["npc_initiative"] = 1
    with pytest.raises(crosswalk.ai.Hold,
                       match="QUALITY_FLOOR_DECISION_INCONSISTENT"):
        crosswalk._valid_decision(bad)


def test_zero_admission_and_no_private_text_in_entries():
    cases = [case(i) for i in range(1, 1001)]
    v1 = [original(i, []) for i in range(1, 1001)]
    v1[0] = original(1, [review("a", "PASS"), review("b", "PASS")])
    selected = [slot(i, "a") for i in range(2, 239)]
    report = crosswalk._apply(cases, v1, [], [], selected, [])
    assert report["candidate_count"] == 1
    assert "reason_cn" not in json.dumps(report)
    assert "target_text" not in json.dumps(report)
    assert report["independence_verified"] is False
    assert report["r50_complete_exclusion_verified"] is False


def test_large_report_uses_bounded_create_only_writer(tmp_path, monkeypatch):
    from contextlib import nullcontext

    monkeypatch.setattr(private, "BASE", tmp_path)
    monkeypatch.setattr(crosswalk.batch.expand, "locked",
                        lambda path: nullcontext())
    monkeypatch.setattr(crosswalk.v3, "_inspect",
                        lambda *args: (
                            {"pool_sha256": "synthetic"}, ["fake-case"],
                            [], {"reviewed_slots": 1, "planned_slots": 1,
                                 "remaining_slots": 0}))
    monkeypatch.setattr(crosswalk.v2, "_inspect",
                        lambda *args: (
                            {"pool_sha256": "synthetic"}, ["fake-case"],
                            [], {"reviewed_slots": 0}))
    monkeypatch.setattr(private, "read_private",
                        lambda *args: b"{}")
    monkeypatch.setattr(crosswalk, "_apply", lambda *args: {
        "schema": crosswalk.SCHEMA,
        "candidate_count": 339,
        "outcome_counts": {"dual_pass_candidate": 339},
        "dual_pass_provenance": {"V1+V1": 159, "V1+V3": 138,
                                 "V1+V2": 11, "V2+V1": 27,
                                 "V3+V1": 4},
        "entries": [{"position": i, "synthetic_padding": "x" * 950}
                    for i in range(339)],
        "gold_promoted": False,
        "train_admitted": 0,
    })
    dest = tmp_path / "r60-real1000-v123-crosswalk-synthetic"

    def invoke(write):
        return crosswalk.inspect(
            tmp_path / "v1", tmp_path / "plan", tmp_path / "v2",
            tmp_path / "v3", dest, write=write)

    preflight = invoke(False)
    assert preflight["status"] == "CROSSWALK_PREFLIGHT_PASS__NO_FILES"
    assert not dest.exists()
    # Simulate the empty 0700 directory left by the earlier failed write.
    dest.mkdir(mode=0o700)
    saved = invoke(True)
    assert saved["status"] == "CROSSWALK_PRIVATE_REPORT_SAVED__NO_ADMISSION"
    out = dest / crosswalk.FILENAME
    assert out.stat().st_size > private.MAX_CAPTURE_BYTES
    assert out.stat().st_size <= crosswalk.MAX_REPORT
    assert out.stat().st_mode & 0o777 == 0o600
    assert json.loads(out.read_text())["candidate_count"] == 339
    with pytest.raises(crosswalk.Hold,
                       match="CROSSWALK_OUTPUT_NONEMPTY_HOLD"):
        invoke(True)
    assert json.loads(out.read_text())["candidate_count"] == 339


def test_oversize_report_fails_without_creating_directory(tmp_path, monkeypatch):
    from contextlib import nullcontext

    monkeypatch.setattr(private, "BASE", tmp_path)
    monkeypatch.setattr(crosswalk.batch.expand, "locked",
                        lambda path: nullcontext())
    monkeypatch.setattr(crosswalk.v3, "_inspect",
                        lambda *args: (
                            {}, [], [], {"reviewed_slots": 0,
                                          "planned_slots": 0,
                                          "remaining_slots": 0}))
    monkeypatch.setattr(crosswalk.v2, "_inspect",
                        lambda *args: ({}, [], [], {"reviewed_slots": 0}))
    monkeypatch.setattr(crosswalk, "_apply", lambda *args: {
        "candidate_count": 1,
        "outcome_counts": {},
        "dual_pass_provenance": {},
        "huge": "x" * (crosswalk.MAX_REPORT + 1),
    })
    dest = tmp_path / "r60-real1000-v123-crosswalk-oversize"
    with pytest.raises(crosswalk.Hold,
                       match="CROSSWALK_REPORT_OVERSIZE_HOLD"):
        crosswalk.inspect(
            tmp_path / "v1", tmp_path / "plan", tmp_path / "v2",
            tmp_path / "v3", dest, write=True)
    assert not dest.exists()
