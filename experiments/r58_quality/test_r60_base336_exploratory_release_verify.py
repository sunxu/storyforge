"""Synthetic-only tests for independent Base336 release verifier."""
import hashlib
import json
import stat

import pytest
import r60_base336_exploratory_release_verify as target
import r60_real_private_batch as private


def release(monkeypatch, tmp_path):
    base = tmp_path / "private"
    base.mkdir(mode=0o700)
    monkeypatch.setattr(private, "BASE", base)
    root = base / "r60-base336-exploratory-test"
    root.mkdir(mode=0o700)
    digests = {}
    for name, count in target.ROWS.items():
        rows = [{"messages": [
            {"role": "user", "content": "合成上文"},
            {"role": "assistant", "content": "合成中间答复"},
            {"role": "user", "content": "合成当前提问"},
            {"role": "assistant", "content": f"合成目标{i}"},
        ]} for i in range(count)]
        raw = b"".join(
            (json.dumps(row, ensure_ascii=False) + "\n").encode()
            for row in rows
        )
        private.write_new(root / f"{name}.jsonl", raw)
        digests[name] = hashlib.sha256(raw).hexdigest()
    manifest = {
        "schema": target.publisher.SCHEMA,
        "status": "EXPLORATORY_TRAIN_VAL_ONLY__NOT_FORMALLY_ADMITTED",
        "case_pool": 336,
        "data_sha256": digests,
        "statistics": {
            "rows": target.ROWS, "stories": target.STORIES,
            "known_world_group_count": 8,
            "crossing_known_world_groups_after_split": 0,
            "excluded_known5": 3,
            "semantic_world_isolation_verified": False,
            "r50_semantic_isolation_verified": False,
            "reviewer_execution_independence_verified": False,
            "input_contract": "THREE_PERSISTED_MESSAGES_NO_SYSTEM",
        },
        "train_admitted": 0, "gpu_started": False,
    }
    private.write_new(root / target.MANIFEST,
                      (json.dumps(manifest) + "\n").encode())
    return root, manifest


def test_valid_release(monkeypatch, tmp_path):
    root, _ = release(monkeypatch, tmp_path)
    result = target.verify(root)
    assert result["status"] == "BASE336_EXPLORATORY_RELEASE_BYTES_VERIFIED__GPU_HOLD"
    assert result["sha256_verified"]
    assert result["train_admitted"] == 0
    assert all(stat.S_IMODE(p.stat().st_mode) == 0o600 for p in root.iterdir())


def test_train_byte_tamper_fails(monkeypatch, tmp_path):
    root, _ = release(monkeypatch, tmp_path)
    path = root / "train.jsonl"
    path.write_bytes(path.read_bytes() + b"x")
    with pytest.raises(target.Hold, match="DATA_DIGEST_MISMATCH_HOLD"):
        target.verify(root)


def test_unexpected_file_fails(monkeypatch, tmp_path):
    root, _ = release(monkeypatch, tmp_path)
    private.write_new(root / "extra.txt", b"unexpected")
    with pytest.raises(target.Hold, match="RELEASE_FILESET_HOLD"):
        target.verify(root)


def test_unbound_split_fails(monkeypatch, tmp_path):
    root, manifest = release(monkeypatch, tmp_path)
    manifest["statistics"]["crossing_known_world_groups_after_split"] = 1
    (root / target.MANIFEST).write_text(json.dumps(manifest))
    with pytest.raises(target.Hold, match="SPLIT_CONTRACT_HOLD"):
        target.verify(root)


def test_permissions_fail(monkeypatch, tmp_path):
    root, _ = release(monkeypatch, tmp_path)
    (root / "train.jsonl").chmod(0o644)
    with pytest.raises(private.Hold):
        target.verify(root)
