"""CPU-only raw vLLM snapshot: capture before failure, integrity, immutability."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

BASE = Path(__file__).resolve().parents[1] / "experiments/r58_quality"
sys.path.insert(0, str(BASE))
spec = importlib.util.spec_from_file_location(
    "r60_generation_snapshot_test", BASE / "r60_generation_snapshot.py")
assert spec and spec.loader
snap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(snap)


def _store(tmp_path):
    output = tmp_path / "private"
    output.mkdir()
    events = []
    worker = SimpleNamespace(
        POLICY="frozen-policy",
        input_digest=lambda row: snap.digest(row),
    )
    store = snap.GenerationSnapshotStore(
        output, worker=worker, model="zai-org/GLM-4-32B-0414",
        revision="a" * 40, runner_sha256="b" * 64,
        emit=lambda name, **data: events.append((name, data)),
    )
    return store, worker, events


def _result(text, finish="stop"):
    return [SimpleNamespace(outputs=[
        SimpleNamespace(text=text, finish_reason=finish)])]


def test_snapshot_persists_primary_and_repair_before_review(tmp_path):
    store, worker, events = _store(tmp_path)
    row = {"private_history": "敏感原文只在私有目录"}
    store.start(1, row)

    class Engine:
        calls = 0
        def generate(self, *args, **kwargs):
            self.calls += 1
            return _result('{"quote":"private 1"}' if self.calls == 1
                           else '{"repairs":[1]}')

    engine = store.wrap(Engine())
    first = engine.generate(["prompt"])
    second = engine.generate(["repair prompt"])
    assert first[0].outputs[0].text == '{"quote":"private 1"}'
    assert second[0].outputs[0].text == '{"repairs":[1]}'
    for index in (1, 2):
        file = store.directory / snap.filename(1, index)
        assert file.stat().st_mode & 0o777 == 0o600
        receipt = snap.read_snapshot(
            file, position=1, generation_index=index,
            row_digest=worker.input_digest(row),
            runner_sha256="b" * 64, model=store.model, revision=store.revision,
            policy=worker.POLICY)
        assert receipt["generation_index"] == index
    assert len(events) == 2
    assert all("敏感原文" not in str(e) and "private 1" not in str(e)
               for e in events)
    with pytest.raises(snap.SnapshotHold, match="SNAPSHOT_TOO_MANY_GENERATIONS_HOLD"):
        engine.generate(["third"])


def test_tampered_text_and_metadata_are_rejected(tmp_path):
    store, worker, _ = _store(tmp_path)
    row = {"source": "private"}
    store.start(1, row)
    engine = store.wrap(SimpleNamespace(
        generate=lambda *a, **kw: _result('{"decision":"HOLD"}')))
    engine.generate([])
    file = store.directory / snap.filename(1, 1)
    original = json.loads(file.read_text())
    original["text"] = '{"decision":"PASS"}'
    file.write_text(json.dumps(original))
    with pytest.raises(snap.SnapshotHold, match="SNAPSHOT_INTEGRITY_HOLD"):
        snap.read_snapshot(
            file, position=1, generation_index=1,
            row_digest=worker.input_digest(row),
            runner_sha256="b" * 64, model=store.model, revision=store.revision,
            policy=worker.POLICY)


def test_snapshot_write_fail_closed_before_validator(tmp_path):
    store, _, _ = _store(tmp_path)
    store.start(1, {"source": "private"})
    file = store.directory / snap.filename(1, 1)
    file.write_text("PREEXISTING")
    engine = store.wrap(SimpleNamespace(
        generate=lambda *a, **kw: _result('{"decision":"HOLD"}')))
    with pytest.raises(FileExistsError):
        engine.generate(["prompt"])
    assert file.read_text() == "PREEXISTING"


def test_generation_with_nonterminal_finish_is_still_captured(tmp_path):
    store, worker, _ = _store(tmp_path)
    row = {"source": "private"}
    store.start(1, row)
    store.wrap(SimpleNamespace(
        generate=lambda *a, **kw: _result('{"partial":', "length")
    )).generate(["prompt"])
    result = snap.read_snapshot(
        store.directory / snap.filename(1, 1),
        position=1, generation_index=1,
        row_digest=worker.input_digest(row), runner_sha256="b" * 64,
        model=store.model, revision=store.revision, policy=worker.POLICY)
    assert result["finish_reason"] == "length"


def test_foreign_directory_and_wrong_identity_rejected(tmp_path):
    store, worker, _ = _store(tmp_path)
    with pytest.raises(snap.SnapshotHold, match="SNAPSHOT_NONEMPTY_HOLD"):
        (store.directory / "foreign").write_text("private")
        snap.GenerationSnapshotStore(
            store.directory, worker=worker, model="model", revision="rev",
            runner_sha256=hashlib.sha256(b"source").hexdigest(),
            emit=lambda *args, **kw: None)



def test_isolation_captures_raw_output_before_review_error(tmp_path):
    """The real isolation runner must snapshot every generation before failure."""
    core_spec = importlib.util.spec_from_file_location(
        "r60_isolation_snapshot_integration",
        BASE / "r60_review_isolation_core.py")
    assert core_spec and core_spec.loader
    core = importlib.util.module_from_spec(core_spec)
    core_spec.loader.exec_module(core)

    output, snapshots, local = (tmp_path / name for name in (
        "receipts", "snapshots", "weights"))
    for directory in (output, snapshots, local):
        directory.mkdir()
    rows = [{"pos": 1}, {"pos": 2}]
    events = []
    state = {"engines": 0, "generates": 0}
    model = "zai-org/GLM-4-32B-0414"
    revision = "a" * 40

    class ReviewerError(ValueError):
        pass

    class Engine:
        def generate(self, *args, **kwargs):
            state["generates"] += 1
            return _result('{"decision":"HOLD","private":"raw not validated"}')

    def engine_factory(**kwargs):
        state["engines"] += 1
        return Engine()

    vllm = SimpleNamespace(LLM=engine_factory)
    tokenizer = SimpleNamespace(
        from_pretrained=lambda *args, **kwargs: object())

    def inference(input_rows, out, name, rev, pos, limit, *args):
        assert limit == 1
        wrapped = vllm.LLM(model=name, revision=rev, tokenizer_revision=rev)
        wrapped.generate(["private prompt"])
        raise ReviewerError("MODEL_NONEXACT_QUOTE_HOLD")

    worker = SimpleNamespace(
        POLICY="synthetic policy", ReviewError=ReviewerError,
        input_digest=core.sha,
        checkpoint_name=lambda pos: f"review_{pos:04d}.private.json",
        read_checkpoint=lambda *args: None,
        inference=inference,
    )
    store = snap.GenerationSnapshotStore(
        snapshots, worker=worker, model=model, revision=revision,
        runner_sha256="b" * 64,
        emit=lambda event, **fields: events.append((event, fields)))
    result = core.run_isolated(
        worker, rows, output, local, model=model, revision=revision,
        limit=2, batch_size=2, max_model_len=32768,
        max_output_tokens=2400, wall_seconds=1200, resume=False,
        hf_tokenizer=tokenizer, vllm=vllm,
        generation_snapshot_store=store)
    assert result["verified"] == 0
    assert result["technical_failures"] == 2
    assert state == {"engines": 1, "generates": 2}
    assert (output / "technical_failure_0001.safe.json").exists()
    assert (output / "technical_failure_0002.safe.json").exists()
    assert sorted(x.name for x in snapshots.iterdir()) == [
        "generation_0001_01.private.json",
        "generation_0002_01.private.json",
    ]
    assert len(events) == 2
    assert all("raw not validated" not in str(e) for e in events)
