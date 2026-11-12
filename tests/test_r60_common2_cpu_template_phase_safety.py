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


def test_new_stage_copies_reviewed_audit_without_modifying_private_input():
    builder = (Path(__file__).resolve().parents[1]
               / "scripts/r60_common2_hf_cpu_stage_v2.py").read_text()
    assert 'AUDIT_RELPATH = "code/experiments/r58_quality/r60_common2_sft_cpu_template_audit.py"' in builder
    assert "if AUDIT_RELPATH not in files" in builder
    assert "files[AUDIT_RELPATH] = audit_bytes" in builder
    assert "files[NEW_WORKER] = worker" in builder
    assert "original_stage_untouched" in builder
    assert "destination.exists()" in builder
