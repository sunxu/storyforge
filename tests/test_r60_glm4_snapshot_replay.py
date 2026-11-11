"""Pure CPU replay of frozen reviewer against signed generated output."""
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
    "r60_glm4_snapshot_replay_test", BASE / "r60_glm4_snapshot_replay.py")
assert spec and spec.loader
replay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(replay)

from r60_generation_snapshot import GenerationSnapshotStore, SnapshotHold


def _fixture(tmp_path, monkeypatch):
    frozen = tmp_path / "runner.py"
    source = tmp_path / "source.private.jsonl"
    snapshots = tmp_path / "snapshots"
    snapshots.mkdir()
    rows = [
        {"blind_id": f"{i:032x}",
         "visible_history": [{"content": "他推开房门，屋内空无一人。"}],
         "target_text": "窗外还在下雨，他缓缓说出了真相。"}
        for i in range(25)
    ]
    source.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n"
                              for row in rows), encoding="utf-8")
    monkeypatch.setattr(replay, "B25_SHA",
                        hashlib.sha256(source.read_bytes()).hexdigest())
    frozen.write_text(
        "import hashlib, json\n"
        "class ReviewError(ValueError): pass\n"
        "class QuoteValidationError(ReviewError):\n"
        "    def __init__(self,invalid_indices):\n"
        "        super().__init__('MODEL_NONEXACT_QUOTE_HOLD')\n"
        "        self.invalid_indices=invalid_indices\n"
        "POLICY='synthetic-frozen'\n"
        "def validate_input(row):\n"
        "    assert len(row['visible_history'])==1\n"
        "def input_digest(row):\n"
        "    return hashlib.sha256(json.dumps(row,sort_keys=True,"
        "separators=(',',':'),ensure_ascii=False).encode()).hexdigest()\n"
        "def validate_response(response,row):\n"
        "    if response['decision'] not in ('PASS','HOLD','REJECT'):\n"
        "        raise ReviewError('MODEL_SCORE_OR_SEVERE_HOLD')\n"
        "    invalid={}\n"
        "    for field, bodies in (('specific_source_quotes',"
        " [m['content'] for m in row['visible_history']]),"
        " ('specific_target_quotes',[row['target_text']])):\n"
        "        for i,quote in enumerate(response[field]):\n"
        "            if not any(quote in body for body in bodies):\n"
        "                invalid.setdefault(field,[]).append(i)\n"
        "    if invalid: raise QuoteValidationError(invalid)\n"
        "    return response['decision']\n"
        "def checkpoint_record(pos,row,response,model,rev):\n"
        "    validate_response(response,row)\n"
        "    return {'response':response}\n"
        "def quote_candidates(row,field):\n"
        "    return ([row['target_text']] if field=='specific_target_quotes'"
        " else [row['visible_history'][0]['content']])\n"
        "def apply_repairs(response,row,invalid,candidates,selection):\n"
        "    copy=dict(response)\n"
        "    copy['specific_target_quotes']=[row['target_text']]\n"
        "    validate_response(copy,row)\n"
        "    return copy\n",
        encoding="utf-8")
    worker = replay.frozen(frozen)
    store = GenerationSnapshotStore(
        snapshots, worker=worker, model=replay.MODEL,
        revision=replay.REV,
        runner_sha256=hashlib.sha256(frozen.read_bytes()).hexdigest(),
        emit=lambda *args, **kw: None)
    return frozen, source, snapshots, rows, store


def _save(store, pos, row, text, secondary=None):
    store.start(pos, row)
    texts = [text] + ([] if secondary is None else [secondary])
    index = iter(texts)
    wrapped = store.wrap(SimpleNamespace(
        generate=lambda *a, **kw: [SimpleNamespace(outputs=[
            SimpleNamespace(text=next(index), finish_reason="stop")])]))
    for _ in texts:
        wrapped.generate(["prompt"])


def _payload(quote):
    return json.dumps({
        "decision": "HOLD",
        "specific_source_quotes": ["他推开房门"],
        "specific_target_quotes": [quote],
    }, ensure_ascii=False)


def test_replay_strict_and_literal_independent(tmp_path, monkeypatch):
    runner, source, snapshots, rows, store = _fixture(tmp_path, monkeypatch)
    selected = [rows[pos - 1] for pos in replay.FAILED_POSITIONS]
    _save(store, 1, selected[0], _payload("窗外还在下雨，他缓缓说出了真相!"))
    result = replay.summarize(SimpleNamespace(
        runner=runner, input=source, snapshots=snapshots,
        output=tmp_path / "summary.safe.json"))
    assert result["replayed_cases"] == 1
    case = result["cases"][0]
    assert case["original_frozen"]["technical_status"] == "REPLAY_FAILED"
    assert case["literal_experiment"]["technical_status"] == "REPLAY_VALIDATED"
    assert case["literal_experiment"]["quality_decision"] == "HOLD"
    assert result["training_authorized"] is False
    assert "窗外" not in json.dumps(result, ensure_ascii=False)


def test_secondary_generation_original_repair_replayed(tmp_path, monkeypatch):
    runner, source, snapshots, rows, store = _fixture(tmp_path, monkeypatch)
    selected = [rows[pos - 1] for pos in replay.FAILED_POSITIONS]
    _save(store, 1, selected[0], _payload("错误引用远离真实原文的文字"),
          secondary='{"repairs":[]}')
    result = replay.summarize(SimpleNamespace(
        runner=runner, input=source, snapshots=snapshots,
        output=tmp_path / "summary.safe.json"))
    assert result["cases"][0]["saved_generations"] == 2
    assert result["cases"][0]["original_frozen"]["technical_status"] == "REPLAY_VALIDATED"


def test_tampered_signed_snapshot_halts_replay(tmp_path, monkeypatch):
    runner, source, snapshots, rows, store = _fixture(tmp_path, monkeypatch)
    selected = [rows[pos - 1] for pos in replay.FAILED_POSITIONS]
    _save(store, 1, selected[0], _payload("原文中不存在"))
    file = snapshots / "generation_0001_01.private.json"
    raw = json.loads(file.read_text())
    raw["text"] = "changed"
    file.write_text(json.dumps(raw))
    with pytest.raises(SnapshotHold, match="SNAPSHOT_INTEGRITY_HOLD"):
        replay.summarize(SimpleNamespace(
            runner=runner, input=source, snapshots=snapshots,
            output=tmp_path / "summary.safe.json"))


def test_absent_primary_or_foreign_file_holds(tmp_path, monkeypatch):
    runner, source, snapshots, _rows, _store = _fixture(tmp_path, monkeypatch)
    (snapshots / "generation_0001_02.private.json").write_text("{}")
    with pytest.raises(replay.ReplayHold, match="SNAPSHOT_PRIMARY_MISSING_HOLD"):
        replay.summarize(SimpleNamespace(
            runner=runner, input=source, snapshots=snapshots,
            output=tmp_path / "summary.safe.json"))
    (snapshots / "generation_0001_02.private.json").unlink()
    (snapshots / "unexpected.txt").write_text("PRIVATE")
    with pytest.raises(replay.ReplayHold, match="SNAPSHOT_NAME_HOLD"):
        replay.summarize(SimpleNamespace(
            runner=runner, input=source, snapshots=snapshots,
            output=tmp_path / "summary.safe.json"))
