"""R60 generation snapshot v1: capture raw vLLM output *before* validation.

This writes private model text to a separate, owner-controlled directory, never
to logs, review receipts or public GitHub. Each case/slot is immutable and
bound to the full input row digest, frozen runner hash and pinned model revision.
No network or vLLM dependency: pure-Python CPU tests.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

SCHEMA = "storyforge_r60_generation_snapshot_private_v1"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
MAX_TEXT_BYTES = 128 * 1024
MAX_SLOTS = 2


class SnapshotHold(ValueError):
    pass


def canonical(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(payload: object) -> str:
    return hashlib.sha256(canonical(payload)).hexdigest()


def filename(position: int, generation_index: int) -> str:
    if not 1 <= position <= 25 or not 1 <= generation_index <= MAX_SLOTS:
        raise SnapshotHold("SNAPSHOT_POSITION_OR_SLOT_HOLD")
    return f"generation_{position:04d}_{generation_index:02d}.private.json"


def verify_directory(path: Path, *, fresh: bool) -> None:
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise SnapshotHold("SNAPSHOT_DIR_HOLD")
    if fresh and any(path.iterdir()):
        raise SnapshotHold("SNAPSHOT_NONEMPTY_HOLD")


def read_snapshot(path: Path, *, position: int, generation_index: int,
                  row_digest: str, runner_sha256: str,
                  model: str, revision: str, policy: str) -> dict:
    if (path.name != filename(position, generation_index)
            or path.is_symlink() or not path.is_file()
            or not 0 < path.stat().st_size <= MAX_TEXT_BYTES + 4096):
        raise SnapshotHold("SNAPSHOT_FILE_HOLD")
    try:
        record = json.loads(path.read_bytes())
    except (ValueError, TypeError, OSError) as exc:
        raise SnapshotHold("SNAPSHOT_JSON_HOLD") from exc
    if not isinstance(record, dict) or set(record) != {
        "schema", "position", "generation_index", "model", "revision",
        "input_sha256", "runner_sha256", "policy", "text",
        "text_sha256", "finish_reason", "receipt_sha256",
    }:
        raise SnapshotHold("SNAPSHOT_SCHEMA_HOLD")
    body = {k: v for k, v in record.items() if k != "receipt_sha256"}
    if (record["schema"] != SCHEMA or record["position"] != position
            or record["generation_index"] != generation_index
            or record["model"] != model or record["revision"] != revision
            or record["input_sha256"] != row_digest
            or record["runner_sha256"] != runner_sha256
            or record["policy"] != policy
            or not isinstance(record["text"], str)
            or not 0 < len(record["text"].encode("utf-8")) <= MAX_TEXT_BYTES
            or not isinstance(record["finish_reason"], str)
            or record["finish_reason"] not in ("stop", "length", "abort")
            or record["text_sha256"] != hashlib.sha256(
                record["text"].encode("utf-8")).hexdigest()
            or record["receipt_sha256"] != digest(body)):
        raise SnapshotHold("SNAPSHOT_INTEGRITY_HOLD")
    return record


class GenerationSnapshotStore:
    def __init__(self, directory: Path, *, worker: object,
                 model: str, revision: str, runner_sha256: str, emit: object):
        verify_directory(directory, fresh=True)
        if not HEX64.fullmatch(runner_sha256):
            raise SnapshotHold("RUNNER_DIGEST_HOLD")
        self.directory = directory
        self.worker = worker
        self.model = model
        self.revision = revision
        self.runner_sha256 = runner_sha256
        self.emit = emit
        self.row = None
        self.position = None
        self.slot = 0

    def start(self, position: int, row: dict) -> None:
        if self.position is not None and position <= self.position:
            raise SnapshotHold("SNAPSHOT_ORDER_HOLD")
        if not 1 <= position <= 25:
            raise SnapshotHold("SNAPSHOT_POSITION_OR_SLOT_HOLD")
        self.position = position
        self.row = row
        self.slot = 0

    def wrap(self, engine: object):
        store = self

        class SnapshotEngine:
            def __getattr__(self, name: str) -> object:
                return getattr(engine, name)

            def generate(self, *args, **kwargs):
                # No result means no snapshot. Engine exceptions propagate.
                result = engine.generate(*args, **kwargs)
                if store.row is None or store.position is None:
                    raise SnapshotHold("SNAPSHOT_CASE_NOT_SET_HOLD")
                if store.slot >= MAX_SLOTS:
                    raise SnapshotHold("SNAPSHOT_TOO_MANY_GENERATIONS_HOLD")
                try:
                    if len(result) != 1 or len(result[0].outputs) != 1:
                        raise SnapshotHold("SNAPSHOT_OUTPUT_SHAPE_HOLD")
                    generated = result[0].outputs[0]
                    content, finish = generated.text, generated.finish_reason
                except (AttributeError, IndexError, TypeError) as exc:
                    raise SnapshotHold("SNAPSHOT_OUTPUT_SHAPE_HOLD") from exc
                if (not isinstance(content, str)
                        or not 0 < len(content.encode("utf-8")) <= MAX_TEXT_BYTES
                        or finish not in ("stop", "length", "abort")):
                    raise SnapshotHold("SNAPSHOT_OUTPUT_BOUNDS_HOLD")
                store.slot += 1
                pos = store.position
                slot = store.slot
                path = store.directory / filename(pos, slot)
                record = {
                    "schema": SCHEMA, "position": pos, "generation_index": slot,
                    "model": store.model, "revision": store.revision,
                    "input_sha256": store.worker.input_digest(store.row),
                    "runner_sha256": store.runner_sha256,
                    "policy": store.worker.POLICY,
                    "text": content, "finish_reason": finish,
                    "text_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                }
                record["receipt_sha256"] = digest(record)
                payload = canonical(record) + b"\n"
                # If private storage fails, abort before the frozen validator:
                # never mark an un-captured generation as successfully reviewed.
                fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY
                             | getattr(os, "O_NOFOLLOW", 0), 0o600)
                with os.fdopen(fd, "wb") as stream:
                    stream.write(payload)
                    stream.flush()
                    os.fsync(stream.fileno())
                read_snapshot(path, position=pos, generation_index=slot,
                              row_digest=store.worker.input_digest(store.row),
                              runner_sha256=store.runner_sha256,
                              model=store.model, revision=store.revision,
                              policy=store.worker.POLICY)
                store.emit("GENERATION_SNAPSHOT_COMMITTED", position=pos,
                           generation_index=slot, private_values_emitted=False)
                return result

        return SnapshotEngine()
