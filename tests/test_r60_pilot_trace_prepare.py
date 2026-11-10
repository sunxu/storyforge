"""CPU-only tests for private A25 traced copy and AST guards."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "experiments/r58_quality/r60_pilot_trace_prepare.py"
spec = importlib.util.spec_from_file_location("trace_prepare", FILE)
assert spec is not None and spec.loader is not None
trace = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trace)


def private_file(path, data):
    path.write_bytes(data)
    os.chmod(path, 0o600)


def fixture(tmp_path):
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    source = root / "input_A"
    source.mkdir(mode=0o700)
    lines = [json.dumps({"synthetic": i}).encode() + b"\n" for i in range(25)]
    private_file(source / "source.private.jsonl", b"".join(lines))
    runner = (
        "import os\n"
        "def inference(rows):\n"
        "    tokenizer = AutoTokenizer.from_pretrained('synthetic')\n"
        "    for row in rows:\n"
        "        ids = encode_chat(tokenizer, row)\n"
        "    engine = LLM(model='synthetic')\n"
        "    params = SamplingParams(temperature=0)\n"
        "    result = engine.generate([], params)\n"
        "    return result\n"
        "def main():\n"
        "    os.environ['VLLM_LOGGING_LEVEL'] = 'WARNING'\n"
        "    return 0\n"
        "from vllm.sampling_params import GuidedDecodingParams\n"
    )
    private_file(source / "runner.py", runner.encode())
    for name in ("token_core.py", "runtime_inputs.py",
                 "runtime_resources.py", "r60_pilot_diagnostic_launcher.py"):
        private_file(source / name, b"# synthetic\n")
    trace.EXPECTED_A_INPUT_SHA256 = trace.digest(b"".join(lines))
    return source, root / "input_A_trace2"


def test_trace_prepare_copy_and_markers(tmp_path):
    source, target = fixture(tmp_path)
    baseline = {p.name: p.read_bytes() for p in source.iterdir()}
    result = trace.prepare(source, target)
    assert result["status"] == "R60_TRACE_A25_PRIVATE_READY__NO_GPU"
    assert result["anchors"] == trace.EXPECTED
    assert result["hf_jobs_submitted"] == 0
    assert result["input_sha256"] == trace.EXPECTED_A_INPUT_SHA256
    assert (target / "source.private.jsonl").read_bytes() == baseline["source.private.jsonl"]
    text = (target / "runner.py").read_text()
    for start, end in trace.EVENTS.values():
        assert f"_r60_diag_event('{start}')" in text
        assert f"_r60_diag_event('{end}')" in text
    assert "VLLM_LOGGING_LEVEL'] = 'INFO'" in text
    assert {p.name: p.read_bytes() for p in source.iterdir()} == baseline
    assert (target.stat().st_mode & 0o777) == 0o700
    assert all((p.stat().st_mode & 0o777) == 0o600 for p in target.iterdir())


def test_repeated_output_rejected(tmp_path):
    source, target = fixture(tmp_path)
    trace.prepare(source, target)
    with pytest.raises(trace.Hold, match="DEST_EXISTS_HOLD"):
        trace.prepare(source, target)


def test_inference_drift_rejected(tmp_path):
    source, target = fixture(tmp_path)
    script = source / "runner.py"
    private_file(script, script.read_bytes().replace(b"engine = LLM", b"engine = Other"))
    with pytest.raises(trace.Hold, match="INFERENCE_ANCHOR_COUNT_HOLD"):
        trace.prepare(source, target)


def test_source_sha_mismatch_rejected(tmp_path):
    source, target = fixture(tmp_path)
    trace.EXPECTED_A_INPUT_SHA256 = "0" * 64
    with pytest.raises(trace.Hold, match="PILOT_A_INPUT_SHA_MISMATCH"):
        trace.prepare(source, target)
