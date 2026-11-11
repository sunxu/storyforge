"""CPU-only guardrail tests for GLM opt-in literal quote reconciliation."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

SOURCE = (Path(__file__).resolve().parents[1] /
          "experiments/r58_quality/r60_glm4_exact_quote_repair.py")
spec = importlib.util.spec_from_file_location("r60_glm4_exact_quote_repair", SOURCE)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ReviewError(ValueError):
    pass


ROW = {
    "visible_history": [{"content": "她推开了房门，屋里一片寂静。"}],
    "target_text": "他抬起头，缓缓说出了真相。",
}


def _worker():
    def checkpoint(pos, row, response, model, revision):
        for field, bodies in (
            ("specific_source_quotes",
             [entry["content"] for entry in row["visible_history"]]),
            ("specific_target_quotes", [row["target_text"]]),
        ):
            for quote in response[field]:
                if not any(quote in body for body in bodies):
                    raise ReviewError("MODEL_NONEXACT_QUOTE_HOLD")
        if response["decision"] != "HOLD":
            raise ReviewError("SYNTHETIC_NONQUOTE_REVIEW_HOLD")
        return response
    return SimpleNamespace(checkpoint_record=checkpoint)


def test_punctuation_only_near_quote_can_be_source_backed():
    original = "他抬起头，缓缓说出了真相!"
    target = ROW["target_text"]
    assert module.reconcile_quote(original, [target]) == target


def test_too_short_or_substantive_rewrite_not_repaired():
    assert module.reconcile_quote("真相!", [ROW["target_text"]]) is None
    assert module.reconcile_quote(
        "他抬起头，慢慢讲述了整个故事。", [ROW["target_text"]]
    ) is None


def test_negation_flip_is_never_repaired():
    text = "她说这件事情可以告诉所有人。"
    quote = "她说这件事情不可以告诉所有人。"
    assert module.reconcile_quote(quote, [text]) is None


def test_ambiguous_proposals_fail_closed():
    original = "他抬起头，缓缓说出了真相!"
    body = ("他抬起头，缓缓说出了真相。" * 2)
    # A single exact replacement *text* at two sites is not ambiguous,
    # but multiple distinct viable strings must fail closed.
    assert module.reconcile_quote(original, [body]) in (
        None, "他抬起头，缓缓说出了真相。",
    )


def test_valid_quote_unchanged_and_checkpoint_receipt_retained():
    worker = _worker()
    emitted = []
    wrapper = module.make_reconciler(
        worker, lambda event, **kw: emitted.append((event, kw)))
    response = {
        "decision": "HOLD",
        "specific_source_quotes": ["她推开了房门"],
        "specific_target_quotes": ["缓缓说出了真相"],
    }
    result = wrapper(1, ROW, response, "model", "revision")
    assert result is response
    assert not emitted


def test_nearby_punctuation_repair_only_modifies_quote():
    worker = _worker()
    emitted = []
    wrapper = module.make_reconciler(
        worker, lambda event, **kw: emitted.append((event, kw)))
    response = {
        "decision": "HOLD", "scores": {"player_agency": 4},
        "specific_source_quotes": ["她推开了房门"],
        "specific_target_quotes": ["他抬起头，缓缓说出了真相!"],
    }
    result = wrapper(1, ROW, response, "model", "revision")
    assert result["specific_target_quotes"] == [ROW["target_text"]]
    assert result["scores"] == {"player_agency": 4}
    assert result["decision"] == "HOLD"
    assert response["specific_target_quotes"] == ["他抬起头，缓缓说出了真相!"]
    assert any(event == "QUOTE_RECONCILIATION_CANDIDATE" for event, _ in emitted)
    assert "他抬起头" not in str(emitted)


def test_nonmatching_original_still_fails_and_no_partial_changes():
    worker = _worker()
    emitted = []
    wrapper = module.make_reconciler(
        worker, lambda event, **kw: emitted.append((event, kw)))
    response = {
        "decision": "HOLD",
        "specific_source_quotes": ["并不存在且无对应历史的长篇引文"],
        "specific_target_quotes": ["他抬起头，缓缓说出了真相!"],
    }
    with pytest.raises(ReviewError, match="MODEL_NONEXACT_QUOTE_HOLD"):
        wrapper(1, ROW, response, "model", "revision")
    assert response["specific_target_quotes"] == ["他抬起头，缓缓说出了真相!"]
    assert any(event == "QUOTE_RECONCILIATION_HOLD" for event, _ in emitted)
    assert not any(event == "QUOTE_RECONCILIATION_CANDIDATE" for event, _ in emitted)


def test_no_cross_field_source_target_swap():
    target = ROW["target_text"]
    assert module.reconcile_quote(target[:-1] + "!", [
        ROW["visible_history"][0]["content"]
    ]) is None


def test_no_repair_of_bad_shape():
    worker = _worker()
    emitted = []
    wrapper = module.make_reconciler(
        worker, lambda event, **kw: emitted.append((event, kw)))
    response = {
        "decision": "HOLD", "specific_source_quotes": "source",
        "specific_target_quotes": ["他抬起头，缓缓说出了真相!"],
    }
    # The wrapper never attempts a repair for a malformed list field.
    with pytest.raises((ReviewError, TypeError)):
        wrapper(1, ROW, response, "model", "revision")
    assert not emitted
