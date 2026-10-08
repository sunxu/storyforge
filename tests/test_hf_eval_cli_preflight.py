import pytest

from scripts.hf_eval_cli_preflight import check_help


def test_help_preflight_accepts_required_options():
    options = ("--model --use_hf --val_dataset --infer_backend --torch_dtype "
               "--quant_method --quant_bits --bnb_4bit_compute_dtype "
               "--max_new_tokens --seed --data_seed --val_dataset_shuffle "
               "--temperature --adapters --result_path")
    check_help(options)


def test_help_preflight_rejects_missing_flag():
    with pytest.raises(ValueError, match="EVAL_CLI_FLAGS_MISSING"):
        check_help("--model --use_hf")
