"""No-secondary-generation mode must preserve frozen validator result."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

SOURCE = (Path(__file__).resolve().parents[1] /
          "experiments/r58_quality/r60_glm4_snapshot_primary_only.py")
spec = importlib.util.spec_from_file_location("r60_glm_snapshot_primary_test", SOURCE)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class ReviewError(ValueError):
    pass


class QuoteValidationError(ReviewError):
    pass


def worker(error=None):
    calls = []

    def checkpoint(pos, row, response, model, rev):
        calls.append("checkpoint")
        if error is not None:
            raise error
        return {"response": response}

    frozen = SimpleNamespace(
        checkpoint_record=checkpoint, QuoteValidationError=QuoteValidationError,
        ReviewError=ReviewError)
    return frozen, calls


def test_nonexact_quote_is_technical_failure_not_secondary_generation():
    frozen, calls = worker(QuoteValidationError("MODEL_NONEXACT_QUOTE_HOLD"))
    events = []
    wrapped = mod.make_primary_only_checkpoint(
        frozen, lambda event, **fields: events.append((event, fields)))
    with pytest.raises(ReviewError, match="MODEL_NONEXACT_QUOTE_HOLD") as error:
        wrapped(1, {"private": "source"}, {}, "model", "revision")
    assert type(error.value) is ReviewError
    assert calls == ["checkpoint"]
    assert len(events) == 1
    assert events[0][0] == "SECONDARY_MODEL_REPAIR_SKIPPED"
    assert events[0][1]["checkpoint_created"] is False
    assert "source" not in str(events)


def test_valid_original_checkpoint_unmodified():
    frozen, calls = worker()
    wrapped = mod.make_primary_only_checkpoint(frozen, lambda *args, **kw: None)
    response = {"decision": "HOLD"}
    result = wrapped(1, {}, response, "model", "rev")
    assert result["response"] is response
    assert calls == ["checkpoint"]


def test_other_review_errors_propagate_without_translation():
    frozen, calls = worker(ReviewError("MODEL_SCORE_OR_SEVERE_HOLD"))
    events = []
    wrapped = mod.make_primary_only_checkpoint(
        frozen, lambda event, **kw: events.append(event))
    with pytest.raises(ReviewError, match="MODEL_SCORE_OR_SEVERE_HOLD"):
        wrapped(1, {}, {}, "model", "rev")
    assert calls == ["checkpoint"]
    assert events == []
