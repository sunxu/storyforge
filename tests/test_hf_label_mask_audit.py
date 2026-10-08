import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "hf_label_mask_audit", Path(__file__).parents[1] / "scripts/hf_label_mask_audit.py")
audit = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(audit)


class _Strategy:
    base_strategy = "last_round"

    def __init__(self, leak=False, missing=False):
        self.leak = leak
        self.missing = missing

    def __call__(self, contexts, types, messages, **kwargs):
        loss = messages[-1].get("loss") is True
        # The final response is token 2; the two suffix tokens are 3 and 4.
        weights = [0.0, 1.0 if loss and not self.missing else 0.0,
                   1.0, 1.0]
        if self.leak:
            weights[0] = 1.0
        return contexts, weights


class _Template:
    _loss_scale = "last_round"

    def __init__(self, strategy):
        self._loss_scale_cache = {"last_round": strategy}
        self.template_meta = type("Meta", (), {"suffix": ["S3", "S4"]})()

    @property
    def loss_scale(self):
        return self._loss_scale_cache[self._loss_scale]

    def _swift_encode(self, inputs):
        contexts = ["H", "A", "S3", "S4"]
        types = [type("T", (), {"name": n}) for n in ("OTHER", "RESPONSE", "SUFFIX", "SUFFIX")]
        cs, ws = self.loss_scale(contexts, types, inputs.messages)
        ids, labels, _ = self._encode_context_list(cs, ws)
        return {"input_ids": ids, "labels": labels}

    def encode(self, row):
        inp = type("Inputs", (), {"messages": row["messages"]})()
        return self._swift_encode(inp)

    def _simplify_context_list(self, contexts, weights, inputs):
        return contexts, weights

    def _encode_context_list(self, contexts, weights=None):
        weights = weights or [0.0] * len(contexts)
        ids = list(range(1, len(contexts) + 1))
        labels = [x if w > 0 else -100 for x, w in zip(ids, weights)]
        return ids, labels, None

    def _add_dynamic_eos(self, *args):
        return None

    def _tokenize(self, context):
        return [1]

    def safe_decode(self, ids):
        return "".join(map(str, ids))


class _RewritingTemplate(_Template):
    def _swift_encode(self, inputs):
        inputs.messages[-1]["content"] = "rewritten by template"
        return super()._swift_encode(inputs)


def _row():
    return {"messages": [
        {"role": "user", "content": "old"},
        {"role": "assistant", "content": "old answer"},
        {"role": "user", "content": "current"},
        {"role": "assistant", "content": "gold", "loss": True},
    ]}


def test_lowercase_ms_swift_context_types_are_normalized():
    assert audit._type_name("response") == "RESPONSE"
    assert audit._type_name("suffix") == "SUFFIX"
    assert audit._type_name("other") == "OTHER"


@pytest.mark.parametrize("suffix_count", [2, 4])
def test_suffix_is_allowed_without_count_threshold(suffix_count):
    # The semantic classifier has no numeric leakage allowance.
    template = _Template(_Strategy())
    capture = audit._LossScaleCapture(template.loss_scale)
    contexts = ["H", "A"] + [f"S{i}" for i in range(suffix_count)]
    types = [type("T", (), {"name": "OTHER"}),
             type("T", (), {"name": "RESPONSE"})] + [
                 type("T", (), {"name": "SUFFIX"}) for _ in range(suffix_count)]
    capture(contexts, types, _row()["messages"])
    template.template_meta.suffix = contexts[2:]
    _, forbidden, final, suffix = audit._semantic_labels(
        template, capture, type("I", (), {"messages": _row()["messages"]})(),
        list(range(1, len(contexts) + 1)))
    assert not (final & forbidden)
    assert len(suffix) == suffix_count


def test_history_leak_fails_even_when_token_looks_like_eos():
    with pytest.raises(ValueError, match="history/system leakage"):
        audit.audit_row(_Template(_Strategy(leak=True)), _row(), 1)


def test_audit_row_passes_and_restores_template_state():
    template = _Template(_Strategy())
    original_cache = template._loss_scale_cache
    original_encode = template._swift_encode.__func__
    audit.audit_row(template, _row(), 1)
    audit.audit_row(template, _row(), 2)
    assert template._loss_scale_cache is original_cache
    assert template._swift_encode.__func__ is original_encode


def test_missing_final_supervision_fails():
    with pytest.raises(ValueError, match="missing final assistant supervision"):
        audit.audit_row(_Template(_Strategy(missing=True)), _row(), 1)


def test_audit_rejects_template_rewriting_gold_content():
    with pytest.raises(ValueError, match="Gold"):
        audit.audit_row(_RewritingTemplate(_Strategy()), _row(), 1)


def test_semantic_input_mismatch_fails():
    template = _Template(_Strategy())
    capture = audit._LossScaleCapture(template.loss_scale)
    types = [type("T", (), {"name": n}) for n in ("OTHER", "RESPONSE", "SUFFIX", "SUFFIX")]
    capture(["H", "A", "S3", "S4"], types, _row()["messages"])
    inputs = type("I", (), {"messages": _row()["messages"]})()
    with pytest.raises(ValueError, match="does not match actual input_ids"):
        audit._semantic_labels(template, capture, inputs, [99, 98, 97, 96])
