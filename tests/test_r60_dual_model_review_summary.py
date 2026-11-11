"""P1 CPU-only: quality decisions, technical failures and provenance are disjoint."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

BASE = Path(__file__).resolve().parents[1] / "experiments/r58_quality"
sys.path.insert(0, str(BASE))
spec = importlib.util.spec_from_file_location(
    "r60_p1_summary", BASE / "r60_dual_model_review_summary.py")
assert spec and spec.loader
p1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p1)
from r60_review_isolation_core import IsolationHold, create_failure, sha


def _fixture(tmp_path):
    a_dir, b_dir = tmp_path / "A", tmp_path / "B"
    a_dir.mkdir()
    b_dir.mkdir()
    rows = [{"blind_id": f"{pos:032x}", "payload": f"private-{pos}"}
            for pos in range(1, 26)]
    def frozen_model():
        def check(path, position, row, model, rev):
            payload = json.loads(path.read_text())
            assert payload["position"] == position
            assert payload["identity"] == sha(row)
            assert payload["model"] == model
            assert payload["revision"] == rev
            assert payload["response"]["decision"] in p1.QUALITY
            return payload
        return SimpleNamespace(
            POLICY="frozen-policy",
            checkpoint_name=lambda pos: f"review_{pos:04d}.private.json",
            read_checkpoint=check,
            input_digest=sha,
        )

    a, b = frozen_model(), frozen_model()

    def write_valid(directory, pos, decision, model, rev):
        (directory / f"review_{pos:04d}.private.json").write_text(
            json.dumps({"position": pos, "identity": sha(rows[pos - 1]),
                        "model": model, "revision": rev,
                        "response": {"decision": decision,
                                     "literary_quality_notes": "PRIVATE"}}))
    def failure(directory, pos, worker, model, rev):
        create_failure(directory / f"technical_failure_{pos:04d}.safe.json",
                       position=pos, worker=worker, row=rows[pos - 1],
                       model=model, revision=rev,
                       reason="MODEL_NONEXACT_QUOTE_HOLD")
    write_valid(a_dir, 1, "PASS", p1.A_MODEL, p1.A_REV)
    write_valid(a_dir, 2, "HOLD", p1.A_MODEL, p1.A_REV)
    write_valid(a_dir, 3, "REJECT", p1.A_MODEL, p1.A_REV)
    failure(a_dir, 4, a, p1.A_MODEL, p1.A_REV)
    write_valid(b_dir, 1, "PASS", p1.B_MODEL, p1.B_REV)
    write_valid(b_dir, 2, "REJECT", p1.B_MODEL, p1.B_REV)
    failure(b_dir, 3, b, p1.B_MODEL, p1.B_REV)
    failure(b_dir, 4, b, p1.B_MODEL, p1.B_REV)
    return rows, a, b, a_dir, b_dir


def _summarize(rows, a, b, a_dir, b_dir):
    sa = p1._one_model(rows, a, a_dir, p1.A_MODEL, p1.A_REV)
    sb = p1._one_model(rows, b, b_dir, p1.B_MODEL, p1.B_REV)
    return p1.summarize(rows, rows, sa, sb)


def test_quality_and_technical_disjoint(tmp_path):
    rows, a, b, a_dir, b_dir = _fixture(tmp_path)
    report = _summarize(rows, a, b, a_dir, b_dir)
    assert report["model_A"]["technical"] == {
        "VERIFIED": 3, "TECHNICAL_FAILURE": 1, "MISSING": 21}
    assert report["model_B"]["technical"] == {
        "VERIFIED": 2, "TECHNICAL_FAILURE": 2, "MISSING": 21}
    assert report["model_A"]["quality_from_verified_only"] == {
        "PASS": 1, "HOLD": 1, "REJECT": 1}
    assert report["model_B"]["quality_from_verified_only"] == {
        "PASS": 1, "HOLD": 0, "REJECT": 1}
    assert report["both_verified"] == 2
    assert report["quality_agreement"] == 1
    assert report["quality_disagreement"] == 1
    assert report["quality_not_comparable"] == 23
    assert report["cases"][2]["A"]["quality_decision"] == "REJECT"
    assert report["cases"][2]["B"]["quality_decision"] is None
    assert report["cases"][2]["quality_comparison"] == "NOT_COMPARABLE"
    assert report["quality_v1_admitted"] == 0
    assert not report["training_authorized"]
    assert "private-1" not in json.dumps(report)


def test_corrupt_or_tampered_failure_holds(tmp_path):
    rows, a, b, a_dir, b_dir = _fixture(tmp_path)
    f = b_dir / "technical_failure_0003.safe.json"
    record = json.loads(f.read_text())
    record["technical_reason_code"] = "MODEL_JSON_HOLD"
    f.write_text(json.dumps(record))
    with pytest.raises(IsolationHold, match="TECHNICAL_RECEIPT_IDENTITY_HOLD"):
        _summarize(rows, a, b, a_dir, b_dir)


def test_corrupt_checkpoint_not_mislabeled_technical_failure(tmp_path):
    rows, a, b, a_dir, b_dir = _fixture(tmp_path)
    checkpoint = a_dir / "review_0001.private.json"
    record = json.loads(checkpoint.read_text())
    record["identity"] = "incorrect"
    checkpoint.write_text(json.dumps(record))
    with pytest.raises(AssertionError):
        _summarize(rows, a, b, a_dir, b_dir)


def test_unknown_or_duplicate_files_fail_closed(tmp_path):
    rows, a, b, a_dir, b_dir = _fixture(tmp_path)
    (a_dir / "untracked.txt").write_text("UNSAFE_CONTENT")
    with pytest.raises(p1.SummaryHold, match="REVIEW_FOREIGN_NAME_HOLD"):
        _summarize(rows, a, b, a_dir, b_dir)
    (a_dir / "untracked.txt").unlink()
    (a_dir / "technical_failure_0001.safe.json").write_text("{}")
    with pytest.raises(p1.SummaryHold, match="REVIEW_DUPLICATE_OR_POSITION_HOLD"):
        _summarize(rows, a, b, a_dir, b_dir)


def test_no_cross_model_guessing_on_reordered_input(tmp_path):
    rows, a, b, a_dir, b_dir = _fixture(tmp_path)
    sa = p1._one_model(rows, a, a_dir, p1.A_MODEL, p1.A_REV)
    sb = p1._one_model(rows, b, b_dir, p1.B_MODEL, p1.B_REV)
    swapped = list(rows)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    with pytest.raises(p1.SummaryHold, match="CROSS_MODEL_SOURCE_OR_ORDER_HOLD"):
        p1.summarize(rows, swapped, sa, sb)


def test_checkpoint_technical_missing_are_mutually_exclusive(tmp_path):
    rows, a, b, a_dir, b_dir = _fixture(tmp_path)
    report = _summarize(rows, a, b, a_dir, b_dir)
    for case in report["cases"]:
        for label in ("A", "B"):
            result = case[label]
            if result["technical_status"] != "VERIFIED":
                assert result["quality_decision"] is None
            if result["technical_status"] == "MISSING":
                assert "technical_reason_code" not in result


def test_input_sha_hard_pin(tmp_path):
    path = tmp_path / "input.jsonl"
    path.write_text('{"private":"not-the-real-frozen-input"}\n')
    worker = SimpleNamespace(validate_input=lambda _: None, input_digest=sha)
    with pytest.raises(p1.SummaryHold, match="INPUT_SHA_HOLD"):
        p1._rows(path, p1.A_INPUT_SHA, worker)
