"""No-private-input tests for strict single-example ms-swift collator shape."""
import ast
from pathlib import Path

import pytest

SRC = (Path(__file__).resolve().parents[1]
       / "experiments/r58_quality/r60_common2_sft_cpu_template_audit.py")
tree = ast.parse(SRC.read_text())
fn = next(node for node in tree.body
          if isinstance(node, ast.FunctionDef) and node.name == "single_batch_ints")
namespace = {"Hold": type("Hold", (ValueError,), {})}
exec(compile(ast.Module(body=[fn], type_ignores=[]), str(SRC), "exec"), namespace)
single_batch_ints = namespace["single_batch_ints"]
Hold = namespace["Hold"]


class MockTensor:
    def __init__(self, data):
        self.data = data

    def detach(self):
        return self

    def cpu(self):
        return self

    def tolist(self):
        return self.data


def test_single_example_rank2_list():
    assert single_batch_ints([[12, 13, 14]]) == [12, 13, 14]


def test_single_example_rank2_tensor():
    assert single_batch_ints(MockTensor([[1, -100, 2]])) == [1, -100, 2]


@pytest.mark.parametrize("value", [
    [1, 2, 3], [],
    [[1], [2]], [[]], [[[1]]],
    [[1.0]], [[True]], [["1"]], None,
])
def test_invalid_batch_dimensions_or_types_fail_closed(value):
    with pytest.raises(Hold, match="SINGLE_BATCH_SHAPE_HOLD"):
        single_batch_ints(value)


def test_integrated_audit_uses_strict_single_batch_reader():
    source = SRC.read_text()
    assert 'batched_ids = single_batch_ints(batch["input_ids"])' in source
    assert 'batched_labels = single_batch_ints(batch["labels"])' in source
    assert "batched_ids[:len(unbatched_ids)] != unbatched_ids" in source
    assert "batched_labels[:len(unbatched_labels)] != unbatched_labels" in source
    assert "audit.audit_row(template, swift_row, number)" in source
    assert '"train_admitted": 0' in source
