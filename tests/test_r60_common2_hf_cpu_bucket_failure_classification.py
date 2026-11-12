"""Synthetic only: HF Bucket read-only failure codes, no private values."""
from pathlib import Path
import importlib.util
import pytest
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("cpu_bucket_guard", ROOT / "scripts/r60_common2_hf_cpu_bucket_guard.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class WithResponse(Exception):
    def __init__(self, status):
        super().__init__("NEVER_PRINT_THIS_ERROR_OR_SECRET")
        self.response = SimpleNamespace(status_code=status)


def test_http_error_codes_do_not_emit_exception_message():
    assert guard.classify_failure(WithResponse(401)) == "REMOTE_AUTHORIZATION_HOLD"
    assert guard.classify_failure(WithResponse(403)) == "REMOTE_AUTHORIZATION_HOLD"
    assert guard.classify_failure(WithResponse(404)) == "REMOTE_BUCKET_OR_PATH_NOT_FOUND_HOLD"
    assert guard.classify_failure(WithResponse(429)) == "REMOTE_RATE_LIMIT_HOLD"
    for code in (500, 502, 503, 504):
        assert guard.classify_failure(WithResponse(code)) == "REMOTE_SERVICE_5XX_HOLD"
    assert guard.classify_failure(WithResponse(418)) == "REMOTE_SDK_OR_SERVICE_HOLD"


def test_httpx_timeout_and_connect_without_private_text():
    httpx = pytest.importorskip('httpx', reason='httpx is installed in the HF SDK Python environment')

    req = httpx.Request("GET", "https://huggingface.co/")
    assert guard.classify_failure(httpx.ReadTimeout("secret", request=req)) == "REMOTE_TIMEOUT_HOLD"
    assert guard.classify_failure(httpx.ConnectError("secret", request=req)) == "REMOTE_CONNECTION_HOLD"
