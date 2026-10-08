from scripts.hf_infer_preflight import REQUIRED, check_help


def test_infer_cli_help_flags():
    assert check_help(" ".join(REQUIRED)) == []


def test_infer_cli_preflight_detects_missing_flag():
    assert check_help(" ".join(REQUIRED[:-1])) == ["--max_new_tokens"]
