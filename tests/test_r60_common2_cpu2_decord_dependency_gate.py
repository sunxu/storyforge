"""No-data regression for the frozen R60 CPU2 decord warning gate."""
from pathlib import Path

WORKER = Path(__file__).resolve().parents[1] / "scripts/r60_common2_hf_cpu_worker_v2.sh"


def test_only_exact_known_decord_warning_is_allowlisted():
    source = WORKER.read_text()
    assert 'expected = ["decord 0.6.0 is not supported on this platform"]' in source
    assert "check.returncode == 1 and lines == expected and stderr_empty" in source
    assert 'importlib.metadata.version("decord") == "0.6.0"' in source
    assert "from decord import cpu, VideoReader" in source
    assert "assert cpu(0) is not None" in source
    assert "R60_CPU2_V2_DEPENDENCY_HOLD" in source
    assert "R60_CPU2_V2_DECORD_IMPORT_HOLD" in source
    assert "import torch" not in source  # No model-weight or GPU startup added.
    assert "swift sft " not in source
    assert 'export CUDA_VISIBLE_DEVICES=""' in source
