"""CPU-only GLM validator observer: direct-call failure stage, exact matches."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT = (Path(__file__).resolve().parents[1] /
          "experiments/r58_quality/r60_glm4_validation_observer.py")
spec = importlib.util.spec_from_file_location("r60_quote_validation_audit", SCRIPT)
assert spec and spec.loader
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class ReviewError(Exception):
    pass


def source_row():
    return {
        "blind_id": "owner-private-id",
        "visible_history": [{"content": "第一段精确引文。"}],
        "target_text": "目标段落的精确引文。",
    }


def worker():
    def validate(result, row):
        for field, bodies in (
            ("specific_source_quotes", [x["content"]
                                        for x in row["visible_history"]]),
            ("specific_target_quotes", [row["target_text"]]),
        ):
            if not all(
                isinstance(q, str) and q.strip()
                and any(q in body for body in bodies)
                for q in result[field]
            ):
                raise ReviewError("MODEL_NONEXACT_QUOTE_HOLD")
        return "VALIDATED"

    return SimpleNamespace(
        input_digest=lambda row: row["blind_id"],
        validate_response=validate,
    )


def test_direct_validator_hook_reaches_failed_matching_check():
    w = worker()
    row = source_row()
    events = []
    original = w.validate_response
    w.validate_response = audit.make_observer(
        w, [row], lambda event, **data: events.append((event, data)))
    response = {
        "decision": "HOLD",
        "specific_source_quotes": ["无法在历史正文中找到"],
        "specific_target_quotes": ["目标段落"],
    }
    with pytest.raises(ReviewError, match="MODEL_NONEXACT_QUOTE_HOLD"):
        w.validate_response(response, row)
    records = [(event, data) for event, data in events
               if event == "VALIDATOR_QUOTE_DIAGNOSTIC"]
    assert len(records) == 2
    assert records[0][1]["not_in_body"] == 1
    assert records[1][1]["not_in_body"] == 0
    assert original is not w.validate_response
    assert "无法在历史正文中找到" not in str(events)
    assert "目标段落" not in str(events)
    assert "owner-private-id" not in str(events)


def test_exact_matching_unmodified():
    w = worker()
    row = source_row()
    events = []
    original = w.validate_response
    wrapped = audit.make_observer(w, [row],
                                  lambda event, **data: events.append((event, data)))
    result = {"decision": "PASS",
              "specific_source_quotes": ["精确引文"],
              "specific_target_quotes": ["精确引文"]}
    assert wrapped(result, row) == original(result, row) == "VALIDATED"
    assert all(data["not_in_body"] == 0 for event, data in events
               if event == "VALIDATOR_QUOTE_DIAGNOSTIC")
    assert result["specific_source_quotes"] == ["精确引文"]


def test_missing_and_invalid_quote_categories():
    row = source_row()
    events = []
    w = worker()
    wrapped = audit.make_observer(
        w, [row], lambda event, **data: events.append((event, data)))
    with pytest.raises((ReviewError, TypeError)):
        wrapped({
            "decision": "PASS",
            "specific_source_quotes": [],
            "specific_target_quotes": [None, "", "x" * 301],
        }, row)
    fields = [data for event, data in events
              if event == "VALIDATOR_QUOTE_DIAGNOSTIC"]
    assert fields[0]["missing"] == 1
    assert fields[1]["non_string"] == 1
    assert fields[1]["empty"] == 1
    assert fields[1]["too_long"] == 1


def test_foreign_input_fails_closed_without_logging_private_values():
    w = worker()
    events = []
    wrapped = audit.make_observer(
        w, [source_row()], lambda event, **data: events.append((event, data)))
    unknown = {**source_row(), "blind_id": "other-private-id"}
    with pytest.raises(ValueError, match="UNEXPECTED_REVIEW_INPUT_HOLD"):
        wrapped({}, unknown)
    assert not events


def test_no_duplicate_input_identities():
    w = worker()
    with pytest.raises(ValueError, match="DUPLICATE_INPUT_IDENTITY_HOLD"):
        audit.make_observer(w, [source_row(), source_row()], lambda *a, **k: None)


def test_no_prompt_or_quote_text_in_logs():
    w = worker()
    row = source_row()
    events = []
    wrapped = audit.make_observer(
        w, [row], lambda event, **data: events.append((event, data)))
    with pytest.raises(ReviewError):
        wrapped({"decision": "HOLD",
                 "specific_source_quotes": ["PRIVATE_UNMATCHED"],
                 "specific_target_quotes": []}, row)
    assert "PRIVATE_UNMATCHED" not in repr(events)
    assert "第一段精确引文" not in repr(events)


def test_frozen_module_checkpoint_global_resolves_wrapped_validator():
    """Important: patch must affect a function's module global lookups."""
    from types import ModuleType

    row = source_row()
    module = ModuleType("synthetic_frozen_runner")
    exec(  # noqa: S102 - synthetic literal, no imported/private source
        "def validate_response(response, row):\\n"
        "    if not all(q in row['target_text'] for q in response['specific_target_quotes']):\\n"
        "        raise ValueError('MODEL_NONEXACT_QUOTE_HOLD')\\n"
        "    return 'PASS'\\n"
        "def checkpoint_record(pos,row,response,model,revision):\\n"
        "    return validate_response(response,row)\\n",
        module.__dict__,
    )
    module.input_digest = lambda item: item["blind_id"]
    events = []
    previous = module.validate_response
    module.validate_response = audit.make_observer(
        module, [row], lambda event, **data: events.append((event, data)))
    with pytest.raises(ValueError, match="MODEL_NONEXACT_QUOTE_HOLD"):
        module.checkpoint_record(
            1, row,
            {"decision": "HOLD", "specific_source_quotes": ["精确引文"],
             "specific_target_quotes": ["错误的目标引文"]},
            "synthetic", "synthetic")
    assert any(event == "VALIDATOR_QUOTE_DIAGNOSTIC"
               and data["field"] == "TARGET"
               and data["not_in_body"] == 1 for event, data in events)
    module.validate_response = previous
