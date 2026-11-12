"""Synthetic tests of wrapper integrity and safe failure; no model/network required."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "r60_common2_wrapped_system_cpu_audit",
    ROOT / "scripts/r60_common2_wrapped_system_cpu_audit.py",
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def fixture(tmp_path):
    folder = tmp_path / "private"
    folder.mkdir(mode=0o700)
    rows = []
    for _ in range(2):
        msgs = [{"role": "user" if i % 2 == 0 else "assistant",
                 "content": f"source-history-{i}"} for i in range(11)]
        msgs.append({"role": "assistant", "content": "source-target"})
        rows.append({
            "schema": "storyforge_r60_source_bound_experimental_sft_v1",
            "input_kind": "SOURCE_BOUND_DERIVED_CONTEXT_NOT_ACTUAL_SENT",
            "supervision_scope": "FINAL_ASSISTANT_ONLY", "messages": msgs,
            "system_prompt": None, "world_card": None, "train_admitted": False,
        })
    raw = b"".join((json.dumps(x) + "\n").encode() for x in rows)
    manifest = {
        "schema": "storyforge_r60_common2_sft_experimental_manifest_private_v1",
        "status": "EXPERIMENTAL_CONTEXT_CONSTRUCTED__NOT_ADMITTED",
        "examples": 2, "window": 11, "train_admitted": 0,
        "r50_complete_exclusion_verified": False,
        "data_sha256": hashlib.sha256(raw).hexdigest(),
    }
    (folder / m.sft.DATA_NAME).write_bytes(raw)
    (folder / m.sft.MANIFEST_NAME).write_text(json.dumps(manifest))
    for p in folder.iterdir(): p.chmod(0o600)
    return folder, rows


def test_prepare_rows_preserves_raw_sources_exactly(tmp_path):
    folder, original = fixture(tmp_path)
    before = {p.name: p.read_bytes() for p in folder.iterdir()}
    wrapped = m.prepare_rows(folder)
    assert len(wrapped) == 2
    for new, old in zip(wrapped, original):
        assert len(new["messages"]) == 13
        assert new["messages"][0] == {
            "role": "system", "content": m.wrapper.PINNED_R27_R52_SYSTEM,
        }
        assert new["messages"][1:] == old["messages"]
        assert new["messages"][-1]["content"] == "source-target"
    assert before == {p.name: p.read_bytes() for p in folder.iterdir()}


def test_missing_snapshot_returns_safe_stage(tmp_path):
    folder, _ = fixture(tmp_path)
    out = m.check(folder, tmp_path / "missing")
    assert out["reason_code"] == "SNAPSHOT_HOLD"
    assert out["gpu_started"] is False and out["files_written"] == 0
    assert out["train_admitted"] == 0


def test_invalid_source_data_is_rejected(tmp_path, monkeypatch):
    folder, _ = fixture(tmp_path)
    manifest = folder / m.sft.MANIFEST_NAME
    doc = json.loads(manifest.read_text())
    doc["data_sha256"] = "0" * 64
    manifest.write_text(json.dumps(doc))
    monkeypatch.setattr(m, "local_snapshot", lambda path: None)
    out = m.check(folder, tmp_path / "pin")
    assert out["reason_code"] == "SOURCE_INPUT_HOLD"
    assert out["original_input_sha_verified"] is False


def test_pinned_system_sha_tampering_fails_closed(tmp_path, monkeypatch):
    folder, _ = fixture(tmp_path)
    monkeypatch.setattr(m.wrapper, "PINNED_R27_R52_SYSTEM", "fictional")
    out = m.check(folder, tmp_path / "pin")
    assert out["reason_code"] == "SYSTEM_PIN_HOLD"
    assert out["wrapped_examples"] == 0


def test_no_secret_exception_text_in_safe_receipt(tmp_path, monkeypatch):
    folder, _ = fixture(tmp_path)
    monkeypatch.setattr(m, "local_snapshot",
                        lambda path: (_ for _ in ()).throw(RuntimeError("SECRET STORY")))
    out = m.check(folder, tmp_path / "pin")
    assert out["reason_code"] == "SNAPSHOT_HOLD"
    assert "SECRET STORY" not in json.dumps(out)


def test_actual_cpu_path_can_be_mocked_without_any_real_weights(tmp_path, monkeypatch):
    folder, rows = fixture(tmp_path)
    monkeypatch.setattr(m, "local_snapshot", lambda path: None)
    import types
    fake_transformers = types.ModuleType("transformers")
    class DummyTok:
        @classmethod
        def from_pretrained(cls, *args, **kwargs):
            assert kwargs["local_files_only"] is True
            return object()
    fake_transformers.AutoTokenizer = DummyTok
    fake_swift = types.ModuleType("swift")
    class Template:
        def set_mode(self, mode):
            assert mode == "train"
    fake_swift.get_processor = lambda *a, **k: object()
    fake_swift.get_template = lambda *a, **k: Template()
    monkeypatch.setitem(sys.modules, "transformers", fake_transformers)
    monkeypatch.setitem(sys.modules, "swift", fake_swift)
    monkeypatch.setattr(m.audit, "bind_text_only_rope", lambda *args: None)
    def mock_inspect(rows, tokenizer, template):
        assert len(rows) == 2
        assert rows[0]["messages"][0]["role"] == "system"
        assert rows[0]["messages"][-1]["content"] == "source-target"
        return {
            "cases":2, "collator_verified":True, "tokenizer_verified":True,
            "tokenizer_input_token_counts":[2500,3100],
            "real_collator_token_counts":[2480,3060],
            "supervised_token_counts":[210,230],
        }
    monkeypatch.setattr(m.audit, "inspect_rows", mock_inspect)
    out = m.check(folder, tmp_path / "pin")
    assert out["status"] == "COMMON2_WRAPPED_SYSTEM_ACTUAL_CPU_COLLATOR_PASS__TRAIN_HOLD"
    assert out["actual_swift_collator_verified"] is True
    assert out["train_admitted"] == 0
    assert out["new_hf_jobs_authorized"] if "new_hf_jobs_authorized" in out else out["hf_jobs_submitted"] == 0
