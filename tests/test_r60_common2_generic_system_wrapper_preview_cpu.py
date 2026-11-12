"""Synthetic-only tests; source rows and historical system remain unmodified."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "r60_common2_generic_system_wrapper_preview_cpu",
    ROOT / "scripts/r60_common2_generic_system_wrapper_preview_cpu.py",
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def fixture(tmp_path, monkeypatch):
    folder = tmp_path / "input"
    folder.mkdir(mode=0o700)
    history = [{"role": "user" if i % 2 == 0 else "assistant",
                "content": f"合成历史{i}"} for i in range(11)]
    rows = [{
        "schema": "storyforge_r60_source_bound_experimental_sft_v1",
        "input_kind": "SOURCE_BOUND_DERIVED_CONTEXT_NOT_ACTUAL_SENT",
        "supervision_scope": "FINAL_ASSISTANT_ONLY",
        "messages": history + [{"role": "assistant", "content": "合成目标"}],
        "system_prompt": None,
        "world_card": None,
        "train_admitted": False,
    } for _ in range(2)]
    raw = b"".join((json.dumps(row, ensure_ascii=False) + "\n").encode() for row in rows)
    manifest = {
        "schema": "storyforge_r60_common2_sft_experimental_manifest_private_v1",
        "status": "EXPERIMENTAL_CONTEXT_CONSTRUCTED__NOT_ADMITTED",
        "examples": 2, "window": 11, "train_admitted": 0,
        "r50_complete_exclusion_verified": False,
        "data_sha256": hashlib.sha256(raw).hexdigest(),
    }
    (folder / m.sft.DATA_NAME).write_bytes(raw)
    (folder / m.sft.MANIFEST_NAME).write_text(json.dumps(manifest))
    for p in folder.iterdir():
        p.chmod(0o600)
    return folder, rows


def test_pinned_r27_r52_system_bytes_are_exact():
    raw = m.PINNED_R27_R52_SYSTEM.encode("utf-8")
    assert len(raw) == 449
    assert hashlib.sha256(raw).hexdigest() == m.SYSTEM_SHA256


def test_preview_only_appends_synthetic_system_in_memory(tmp_path, monkeypatch):
    folder, rows = fixture(tmp_path, monkeypatch)
    before = {p.name: p.read_bytes() for p in folder.iterdir()}
    result = m.preview(folder)
    assert result["status"] == "COMMON2_GENERIC_SYSTEM_IN_MEMORY_WRAPPER_PREVIEW_PASS__TRAIN_HOLD"
    assert result["wrapped_examples"] == 2
    assert result["synthetic_system_messages_added"] == 2
    assert result["source_messages_preserved"] is True
    assert result["original_targets_unchanged"] is True
    assert result["supervision_only_final_assistant"] is True
    assert result["train_admitted"] == 0
    assert result["new_swift_collator_verified"] is False
    assert result["files_written"] == 0
    assert before == {p.name: p.read_bytes() for p in folder.iterdir()}
    assert "合成目标" not in json.dumps(result, ensure_ascii=False)


def test_changed_system_pin_fails_closed(tmp_path, monkeypatch):
    folder, _ = fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(m, "PINNED_R27_R52_SYSTEM", "not the archived system")
    out = m.preview(folder)
    assert out["reason_code"] == "SYSTEM_PIN_MISMATCH_HOLD"
    assert out["train_admitted"] == 0


def test_modified_source_manifest_rejected(tmp_path, monkeypatch):
    folder, _ = fixture(tmp_path, monkeypatch)
    manifest = folder / m.sft.MANIFEST_NAME
    doc = json.loads(manifest.read_text())
    doc["data_sha256"] = "0" * 64
    manifest.write_text(json.dumps(doc))
    out = m.preview(folder)
    assert out["reason_code"] == "PRIVATE_EXPERIMENT_CONTRACT_HOLD"
    assert out["files_written"] == 0


def test_unknown_private_exception_never_leaks(tmp_path, monkeypatch):
    folder, _ = fixture(tmp_path, monkeypatch)
    def reject(*args):
        raise RuntimeError("private original response must not escape")
    monkeypatch.setattr(m.audit, "validate_payload", reject)
    out = m.preview(folder)
    assert out["reason_code"] == "INPUT_OR_RUNTIME_HOLD"
    assert "private original" not in json.dumps(out)
    assert out["train_admitted"] == 0
