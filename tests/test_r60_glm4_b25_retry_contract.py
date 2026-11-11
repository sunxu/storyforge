"""CPU-only R60 GLM B25 strict old 25 -> selected 12 retry + repair."""
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
    "r60_glm4_retry_contract", BASE / "r60_glm4_b25_retry_contract.py")
assert spec and spec.loader
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)
from r60_review_isolation_core import create_failure  # noqa: E402


def cases(tmp_path):
    old, fresh = tmp_path / "original", tmp_path / "retry"
    old.mkdir()
    fresh.mkdir()
    rows = [
        {"blind_id": f"{n:032x}", "visible_history": [
            {"role": "user", "content": "原文引文"},
        ], "target_text": "确切的目标原文"} for n in range(1, 26)
    ]

    def check(path, pos, row, model, revision):
        assert model == contract.MODEL and revision == contract.REVISION
        if not path.is_file():
            return None
        record = json.loads(path.read_text())
        if record["position"] != pos or record["blind_id"] != row["blind_id"]:
            raise ValueError("RECORD_MISMATCH")
        return record

    def checkpoint_name(pos):
        return f"review_{pos:04d}.private.json"

    import r60_review_isolation_core as core

    worker = SimpleNamespace(
        POLICY="frozen-policy",
        checkpoint_name=checkpoint_name,
        read_checkpoint=check,
        input_digest=lambda row: core.sha(row),
        checkpoint_record=lambda pos, row, response, model, revision: response,
    )
    for pos in contract.VALID_POSITIONS:
        (old / checkpoint_name(pos)).write_text(json.dumps(
            {"position": pos, "blind_id": rows[pos - 1]["blind_id"]}))
    for pos in contract.FAILED_POSITIONS:
        create_failure(old / core.failure_name(pos), position=pos,
                       worker=worker, row=rows[pos - 1],
                       model=contract.MODEL, revision=contract.REVISION,
                       reason=contract.REASON)
    return worker, rows, old, fresh


def test_verified_baseline_exact12(tmp_path, capsys):
    worker, rows, old, fresh = cases(tmp_path)
    selected, origins = contract.verify_baseline(worker, rows, old, fresh)
    assert origins == (1, 5, 6, 7, 9, 12, 15, 20, 22, 23, 24, 25)
    assert [x["blind_id"] for x in selected] == [
        rows[i - 1]["blind_id"] for i in origins]
    assert len(list(old.iterdir())) == 25
    assert "RETRY_BASELINE_VERIFIED" in capsys.readouterr().out


def test_refuses_empty_or_tampered_or_foreign_baseline(tmp_path):
    worker, rows, old, fresh = cases(tmp_path)
    (old / "technical_failure_0001.safe.json").unlink()
    with pytest.raises(contract.IsolationHold, match="RETRY_BASELINE_INVENTORY_HOLD"):
        contract.verify_baseline(worker, rows, old, fresh)
    (old / "technical_failure_0001.safe.json").write_text("{}")
    with pytest.raises(contract.IsolationHold):
        contract.verify_baseline(worker, rows, old, fresh)


def test_refuses_output_with_any_old_data(tmp_path):
    worker, rows, old, fresh = cases(tmp_path)
    (fresh / "review_0001.private.json").write_text("{}")
    with pytest.raises(contract.IsolationHold, match="RETRY_PATH_OR_INPUT_HOLD"):
        contract.verify_baseline(worker, rows, old, fresh)


def test_exact_source_singleton_preserves_text_and_original(tmp_path):
    worker, rows, _old, _fresh = cases(tmp_path)
    logged = []
    observed = contract.quote_shape_diagnostic(
        worker, lambda *args, **kw: logged.append((args, kw)), repair=True)
    data = {"specific_source_quotes": "原文引文",
            "specific_target_quotes": ["确切的目标原文"],
            "decision": "PASS"}
    got = observed(1, rows[0], data, contract.MODEL, contract.REVISION)
    assert got["specific_source_quotes"] == ["原文引文"]
    assert data["specific_source_quotes"] == "原文引文"
    assert any(x[0][0] == "QUOTE_SHAPE_REPAIR" for x in logged)
    assert all("原文引文" not in str(event) for event in logged)


def test_inexact_string_never_normalized(tmp_path):
    worker, rows, _old, _fresh = cases(tmp_path)
    logged = []
    observed = contract.quote_shape_diagnostic(
        worker, lambda *args, **kw: logged.append((args, kw)), repair=True)
    data = {"specific_source_quotes": "并不存在的伪造文字",
            "specific_target_quotes": ["确切的目标原文"]}
    assert observed(1, rows[0], data, contract.MODEL, contract.REVISION) is data
    assert not any(x[0][0] == "QUOTE_SHAPE_REPAIR" for x in logged)


def test_overlimit_exact_dedup_preserves_all_distinct_quotes(tmp_path):
    worker, rows, _old, _fresh = cases(tmp_path)
    logs = []
    values = ["原文引文"] * 13
    data = {"specific_source_quotes": values,
            "specific_target_quotes": ["确切的目标原文"]}
    result = contract.quote_shape_diagnostic(
        worker, lambda *args, **kw: logs.append((args, kw)), repair=True)(
            1, rows[0], data, contract.MODEL, contract.REVISION)
    assert result["specific_source_quotes"] == ["原文引文"]
    assert data["specific_source_quotes"] == values


def test_overlimit_distinct_never_drops_evidence(tmp_path):
    worker, rows, _old, _fresh = cases(tmp_path)
    data = {"specific_source_quotes": ["原文引文"] * 12 + ["不存在"],
            "specific_target_quotes": ["确切的目标原文"]}
    out = contract.quote_shape_diagnostic(
        worker, lambda *args, **kw: None, repair=True)(
            1, rows[0], data, contract.MODEL, contract.REVISION)
    assert out is data
