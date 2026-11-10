"""CPU-only fail-closed checks for the scoped synthetic 32K worker gate."""
import json
from pathlib import Path

import pytest

from storyforge_dataset.generation_eval.synthetic_32k import SYNTHETIC_SENTENCE
from storyforge_dataset.generation_eval.synthetic_gate import (
    CALIBRATED_SHA256,
    _is_exact_synthetic_text,
    authorize_synthetic_profile,
)
from storyforge_dataset.generation_eval.worker import WorkerError


def test_exact_synthetic_text_only():
    p = ("请确认你正在处理一次人工生成的长上下文运行时测试，"
         "请简洁概括下文重复结构，不要猜测真实人物或故事。\n")
    s = "\n结束。请输出一句简短中文确认。"
    assert _is_exact_synthetic_text(p + SYNTHETIC_SENTENCE * 3 + s)
    assert not _is_exact_synthetic_text(p + SYNTHETIC_SENTENCE + "恶意文本" + s)
    assert not _is_exact_synthetic_text(p + "真实历史消息" + s)
    assert not _is_exact_synthetic_text(p + s)


@pytest.mark.parametrize("role", ("A", "B", "challenger"))
def test_calibrated_sha_is_distinct_per_role(role):
    sha = CALIBRATED_SHA256[role]
    assert len(sha) == 64
    assert len(set(CALIBRATED_SHA256.values())) == 3


def test_exact_hash_gate_rejects_other_input_before_inference(tmp_path):
    root = Path(__file__).parents[1]
    frozen = root / "experiments/r60_quality/p4_generation_profile_frozen_v1.json"
    auth = root / "experiments/r60_quality/p4_generation_execution_authorization_20261110.json"
    user_input = tmp_path / "inputs.jsonl"
    user_input.write_text(
        json.dumps({"sample_id": "r60-synthetic-32k-a",
                    "messages": [{"role": "user", "content": "hello"}]}) + "\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "schema": "storyforge_r60_generation_input_manifest_v1",
        "record_count": 1,
        "sha256": CALIBRATED_SHA256["A"],
        "max_input_tokens": 28672,
        "max_new_tokens": 4096,
        "seed": 42,
    }), encoding="utf-8")
    with pytest.raises(WorkerError, match="SYNTHETIC_INPUT_VERIFICATION_FAILED"):
        authorize_synthetic_profile(
            frozen_path=frozen, authorization_path=auth,
            manifest_path=manifest, input_path=user_input,
            model_role="A",
        )


def test_synthetic_worker_cli_rejects_bad_input_without_gpu(tmp_path, capsys):
    from storyforge_dataset.generation_eval.worker_cli import main
    root = Path(__file__).parents[1]
    frozen = root / "experiments/r60_quality/p4_generation_profile_frozen_v1.json"
    auth = root / "experiments/r60_quality/p4_generation_execution_authorization_20261110.json"
    bad_input = tmp_path / "inputs.jsonl"
    bad_input.write_text('{"sample_id":"bad","messages":[]}', encoding="utf-8")
    bad_manifest = tmp_path / "manifest.json"
    bad_manifest.write_text("{}", encoding="utf-8")
    code = main([
        "--model-role", "A", "--profile", str(frozen),
        "--synthetic-authorization", str(auth),
        "--manifest", str(bad_manifest),
        "--input", str(bad_input),
        "--output-dir", "/output/should-not-create",
        "--repo-root", str(root),
    ])
    assert code == 2
    safe = json.loads(capsys.readouterr().out)
    assert safe["status"] == "GENERATION_WORKER_HOLD"
    assert safe["reason_code"] == "SYNTHETIC_INPUT_VERIFICATION_FAILED"
    assert safe["gpu_started"] is False
    assert safe["inference_started"] is False
    assert safe["training_started"] is False
