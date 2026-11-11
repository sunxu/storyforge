"""Pure CPU regression for Qwen position-7 signed snapshot/replay."""
import hashlib
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest
from types import SimpleNamespace

ROOT = pathlib.Path(__file__).resolve().parents[1] / "experiments" / "r58_quality"
sys.path.insert(0, str(ROOT))
from r60_generation_snapshot import GenerationSnapshotStore  # noqa: E402
import r60_qwen_snapshot_cpu_replay as replay  # noqa: E402

FAKE_RUNNER = '''
import hashlib
import json
POLICY = "synthetic-v1"
def validate_input(row):
    assert "blind_id" in row
def input_digest(row):
    return hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()
def checkpoint_record(pos, row, response, model, revision):
    if response.get("decision") != "HOLD":
        raise ValueError("synthetic frozen rejection")
    return {"response": {"decision": "HOLD"}}
'''


class QwenSnapshotReplayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.runner = self.root / "runner.py"
        self.runner.write_text(FAKE_RUNNER)
        self.source = self.root / "source.private.jsonl"
        self.rows = [{"blind_id": f"case-{i}"} for i in range(1, 26)]
        raw = "".join(json.dumps(row) + "\n" for row in self.rows).encode()
        self.source.write_bytes(raw)
        self.previous_sha = replay.SOURCE_SHA
        replay.SOURCE_SHA = hashlib.sha256(raw).hexdigest()
        self.addCleanup(setattr, replay, "SOURCE_SHA", self.previous_sha)
        spec = importlib.util.spec_from_file_location("fake_qwen_runner", self.runner)
        self.worker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.worker)
        self.snapshots = self.root / "snapshots"
        self.snapshots.mkdir()
        self.events = []

    def capture(self, text, finish_reason="stop"):
        store = GenerationSnapshotStore(
            self.snapshots, worker=self.worker, model=replay.MODEL,
            revision=replay.REV,
            runner_sha256=hashlib.sha256(self.runner.read_bytes()).hexdigest(),
            emit=lambda event, **kwargs: self.events.append((event, kwargs)))
        store.start(7, self.rows[6])
        engine = SimpleNamespace(generate=lambda: [
            SimpleNamespace(outputs=[
                SimpleNamespace(text=text, finish_reason=finish_reason)])])
        return store.wrap(engine).generate()

    def test_valid_primary_replays_without_mutation(self):
        self.capture('{"decision":"HOLD"}')
        before = sorted((p.name, p.read_bytes()) for p in self.snapshots.iterdir())
        result = replay.inspect(self.runner, self.source, self.snapshots)
        after = sorted((p.name, p.read_bytes()) for p in self.snapshots.iterdir())
        self.assertEqual(before, after)
        self.assertEqual(result["technical_status"], "REPLAY_VALIDATED")
        self.assertEqual(result["quality_decision"], "HOLD")
        self.assertEqual(result["quality_v1_admitted"], 0)
        self.assertEqual(result["authenticated_snapshots"], 1)

    def test_tampering_is_rejected(self):
        self.capture('{"decision":"HOLD"}')
        path = next(self.snapshots.iterdir())
        data = json.loads(path.read_text())
        data["text"] = "tampered"
        path.write_text(json.dumps(data))
        with self.assertRaises(Exception):
            replay.inspect(self.runner, self.source, self.snapshots)

    def test_invalid_json_is_technical_failure(self):
        self.capture("not json")
        result = replay.inspect(self.runner, self.source, self.snapshots)
        self.assertEqual(result["reason_code"], "MODEL_JSON_HOLD")
        self.assertIsNone(result["quality_decision"])

    def test_incomplete_generation_is_technical_failure(self):
        self.capture('{"decision":"HOLD"}', finish_reason="length")
        result = replay.inspect(self.runner, self.source, self.snapshots)
        self.assertEqual(result["reason_code"], "MODEL_GENERATION_INCOMPLETE_HOLD")

    def test_unknown_files_are_rejected(self):
        self.capture('{"decision":"HOLD"}')
        (self.snapshots / "foreign.txt").write_text("x")
        with self.assertRaises(Exception):
            replay.inspect(self.runner, self.source, self.snapshots)


if __name__ == "__main__":
    unittest.main()
