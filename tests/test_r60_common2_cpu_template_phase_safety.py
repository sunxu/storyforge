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


def test_qwen38_processor_and_template_are_explicit():
    assert 'get_processor(str(args.snapshot), model_type="qwen3_5")' in SRC
    assert 'processor, template_type="qwen3_8"' in SRC
    assert 'loss_scale="last_round", max_length=CEILING' in SRC
    assert 'add_non_thinking_prefix=False' in SRC
    assert 'from collections.abc import Mapping' in SRC
    assert 'ids = output.get("input_ids") if isinstance(output, Mapping) else output' in SRC
    assert 'any(type(x) is not int for x in ids)' in SRC
    assert 'raise Hold("TOKENIZER_OUTPUT_HOLD")' in SRC
    assert "eval(" not in SRC
    assert "traceback.print_exc" not in SRC


def test_model_free_qwen38_rope_is_text_only_and_fails_closed():
    assert "def bind_text_only_rope(template, snapshot: Path)" in SRC
    assert "from transformers.models.qwen3_5.modeling_qwen3_5 import Qwen3_5Model" in SRC
    assert "config_only = SimpleNamespace(config=config)" in SRC
    assert 'getattr(config, "model_type", None) != "qwen3_5"' in SRC
    assert 'type(template).__name__ != "Qwen3_8Template"' in SRC
    assert 'kwargs.get("image_grid_thw") is not None' in SRC
    assert 'kwargs.get("video_grid_thw") is not None' in SRC
    assert "mm_types is None" in SRC
    assert "torch.any(mm_types != 0)" in SRC
    assert "Qwen3_5Model.get_rope_index(" in SRC
    assert "template._get_get_rope_index = lambda: text_rope" in SRC
    assert "bind_text_only_rope(template, args.snapshot)" in SRC
    assert '"TEXT_ONLY_ROPE_SETUP"' in SRC
    assert '"model_weights_loaded": False' in SRC
    assert '"native_template_token_parity_verified": False' in SRC
    assert "return_dummy_model=True" not in SRC
    assert "get_model_processor(" not in SRC
