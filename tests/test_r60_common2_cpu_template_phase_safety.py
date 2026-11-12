"""Synthetic-only contract for privacy-preserving CPU template audit diagnostics."""
from pathlib import Path

SRC = (Path(__file__).resolve().parents[1]
       / "experiments/r58_quality/r60_common2_sft_cpu_template_audit.py").read_text()


def test_safe_phases_are_explicit_and_do_not_disclose_input():
    for phase in (
        "SNAPSHOT_CHECK", "PRIVATE_INPUT_CHECK", "TOKENIZER_LOAD",
        "SWIFT_PROCESSOR_LOAD", "SWIFT_TEMPLATE_INIT",
        "TOKENIZER_ENCODE", "SWIFT_COLLATOR_AUDIT",
    ):
        assert '"' + phase + '"' in SRC
    assert 'args._safe_phase + "_HOLD"' in SRC
    assert "phase=set_phase" in SRC
    assert 'phase("TOKENIZER_ENCODE")' in SRC
    assert 'phase("SWIFT_COLLATOR_AUDIT")' in SRC
    assert "except Exception:" in SRC
    assert '"private_values_emitted": False' in SRC
    assert '"train_admitted": 0' in SRC
    assert "traceback.print_exc" not in SRC
    assert "repr(exc)" not in SRC
