#!/usr/bin/env python3
"""R58 G1: one already-pinned CANCELED HF Job's existing TensorBoard scalars.

Scope: reads only the exact Job's small, previously discovered event file via
HfFileSystem in the authenticated Owner Mac environment. Never launches a Job,
reads JSONL training examples, commands or other logs, or exports private IDs.
It verifies TFRecord CRC32C and decodes a bounded subset of protobuf Event /
Summary.Value fields with Python's standard library; no TensorFlow required.

This is observational event metadata, not independent optimizer-update proof.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import re
import stat
import struct
import sys

PREFIX = "hf://buckets/adradar/storyforge-training/runs"
OUTPUT_VERSION = "v0-20261008-054349"  # one version discovered from the target Job scope
EXPECTED_BYTES = 10252  # exact listing pin, fail on drift
PRIVATE_SCHEMA = "r58_round1_g1_gpu_signal_priority_case_private_v1"
SAFE_SCHEMA = "r58_g1_one_job_tensorboard_scalar_readonly_safe_v1"
ID_RE = re.compile(r"[a-f0-9]{24}\Z")
SHA_RE = re.compile(r"[a-f0-9]{64}\Z")
EVENT_NAME = re.compile(r"events\.out\.tfevents\.[A-Za-z0-9._-]{1,240}\Z")
MAX_EVENT_BYTES = 64 * 1024
MAX_EVENTS = 300
MAX_SUBVALUES = 200
# Only emit known training-metric tags. Everything else is counted, not printed.
TAGS = frozenset({
    "train/loss", "train/grad_norm", "train/learning_rate", "train/epoch",
    "train/token_acc", "train/global_step", "train/steps", "train/train_loss",
    "eval/loss", "eval/accuracy", "eval/epoch", "loss", "grad_norm",
    "learning_rate", "epoch", "token_acc", "global_step", "train_loss",
    "eval_loss", "train/lr", "lr",
})


class Hold(Exception):
    pass


def load_private_ledger(path: Path) -> dict:
    root = Path.home() / ".storyforge-r58-private"
    if not path.is_absolute() or not path.is_relative_to(root) or path.is_symlink():
        raise Hold("private scope invalid")
    cur = root
    for component in path.relative_to(root).parts[:-1]:
        cur = cur / component
        if cur.is_symlink():
            raise Hold("symlinked private root")
    fd = os.open(str(path), os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as f:
        s = os.fstat(f.fileno())
        if not stat.S_ISREG(s.st_mode) or s.st_mode & 0o077 or not 0 < s.st_size <= 12000:
            raise Hold("private ledger mode or size invalid")
        contents = f.read(12001)
    if len(contents) > 12000:
        raise Hold("private ledger oversize")
    try:
        x = json.loads(contents)
    except (ValueError, UnicodeError) as e:
        raise Hold("bad private JSON") from e
    if not isinstance(x, dict):
        raise Hold("bad private schema")
    job = x.get("hf_job_id_PRIVATE")
    digest = x.get("prior_gpu_log_sha256_PRIVATE")
    if (x.get("schema") != PRIVATE_SCHEMA or not isinstance(job, str)
        or ID_RE.fullmatch(job) is None or not isinstance(digest, str)
        or SHA_RE.fullmatch(digest) is None
        or x.get("namespace") != "adradar" or x.get("stage") != "CANCELED"
        or x.get("indicator_classes") != ["TRAINING_LOSS_GRAD_TELEMETRY"]
        or x.get("status") != "ONE_POTENTIAL_LOG_INDICATOR__PROOF_NOT_ESTABLISHED"
        or x.get("update_proof_status") != "PENDING_PRIMARY_RUN_ARTIFACT"
        or x.get("g1_clearance") != "HOLD" or x.get("expansion_allowed") is not False):
        raise Hold("private identity or target condition mismatch")
    return x


def crc32c(data: bytes) -> int:
    """CRC32C (Castagnoli), reflected polynomial; pure stdlib."""
    c = 0xFFFFFFFF
    for b in data:
        c ^= b
        for _ in range(8):
            c = (c >> 1) ^ (0x82F63B78 if (c & 1) else 0)
    return (~c) & 0xFFFFFFFF


def masked_crc(data: bytes) -> int:
    c = crc32c(data)
    return (((c >> 15) | (c << 17)) + 0xA282EAD8) & 0xFFFFFFFF


def records(buf: bytes):
    pos = 0
    count = 0
    while pos < len(buf):
        if len(buf) - pos < 16:
            raise Hold("incomplete TFRecord")
        header = buf[pos:pos + 8]
        length = struct.unpack("<Q", header)[0]
        length_crc = struct.unpack_from("<I", buf, pos + 8)[0]
        if length_crc != masked_crc(header) or length > MAX_EVENT_BYTES:
            raise Hold("TFRecord header CRC or length invalid")
        end = pos + 12 + length
        if end + 4 > len(buf):
            raise Hold("incomplete TFRecord payload")
        payload = buf[pos + 12:end]
        data_crc = struct.unpack_from("<I", buf, end)[0]
        if data_crc != masked_crc(payload):
            raise Hold("TFRecord payload CRC invalid")
        count += 1
        if count > MAX_EVENTS:
            raise Hold("too many event records")
        yield payload
        pos = end + 4
    if count < 1:
        raise Hold("empty TFRecord")


def read_varint(data: bytes, pos: int):
    number = 0
    for shift in range(0, 70, 7):
        if pos >= len(data):
            raise Hold("truncated protobuf varint")
        b = data[pos]
        pos += 1
        number |= (b & 127) << shift
        if not (b & 128):
            return number, pos
    raise Hold("protobuf varint too large")


def fields(data: bytes):
    pos = 0
    n = 0
    while pos < len(data):
        n += 1
        if n > 2000:
            raise Hold("protobuf excessive fields")
        key, pos = read_varint(data, pos)
        number, wire = key >> 3, key & 7
        if number <= 0:
            raise Hold("invalid field number")
        if wire == 0:
            value, pos = read_varint(data, pos)
        elif wire == 1:
            if pos + 8 > len(data):
                raise Hold("truncated fixed64")
            value = data[pos:pos + 8]
            pos += 8
        elif wire == 2:
            length, pos = read_varint(data, pos)
            if length > len(data) - pos:
                raise Hold("truncated length-delimited protobuf field")
            value = data[pos:pos + length]
            pos += length
        elif wire == 5:
            if pos + 4 > len(data):
                raise Hold("truncated fixed32")
            value = data[pos:pos + 4]
            pos += 4
        else:
            raise Hold("unsupported protobuf wire type")
        yield number, wire, value


def scan_summary(blob: bytes) -> tuple[int, list[tuple[str, float]]]:
    total_values = 0
    scalars = []
    for number, wire, value in fields(blob):
        if (number, wire) != (1, 2):
            continue
        total_values += 1
        if total_values > MAX_SUBVALUES:
            raise Hold("too many Summary.Value fields")
        tag = None
        simple_value = None
        for fnum, fwire, fval in fields(value):
            if (fnum, fwire) == (1, 2):
                try:
                    decoded = fval.decode("utf-8", errors="strict")
                except UnicodeError:
                    continue
                if decoded in TAGS:
                    tag = decoded
            elif (fnum, fwire) == (2, 5):
                simple_value = struct.unpack("<f", fval)[0]
        if tag is not None and simple_value is not None and math.isfinite(simple_value):
            scalars.append((tag, simple_value))
    return total_values, scalars


def parse_event_file(blob: bytes) -> dict:
    summary_count = 0
    scalar_values = 0
    all_event_steps = set()
    metric_steps: dict[str, list[dict]] = {}
    record_count = 0
    for event in records(blob):
        record_count += 1
        steps = []
        summaries = []
        for fnum, fwire, fval in fields(event):
            if (fnum, fwire) == (2, 0):
                if fval > 1_000_000_000:
                    raise Hold("implausible Event step")
                steps.append(fval)
            elif (fnum, fwire) == (5, 2):
                summaries.append(fval)
        step = steps[-1] if steps else None
        if step is not None:
            all_event_steps.add(step)
        for summary in summaries:
            summary_count += 1
            count, scalar_pairs = scan_summary(summary)
            scalar_values += count
            for tag, number in scalar_pairs:
                if step is None:
                    continue
                if sum(map(len, metric_steps.values())) >= MAX_SUBVALUES:
                    raise Hold("too many metric samples")
                metric_steps.setdefault(tag, []).append({"step": step, "value": round(number, 8)})
    return {
        "event_records_crc32c_verified": record_count,
        "summary_event_count": summary_count,
        "summary_values_seen": scalar_values,
        "event_steps_observed": sorted(all_event_steps),
        "approved_scalar_metrics": metric_steps,
        "approved_scalar_sample_count": sum(map(len, metric_steps.values())),
    }


def run(path: Path) -> dict:
    identity = load_private_ledger(path)
    jobid = identity["hf_job_id_PRIVATE"]
    root = f"{PREFIX}/{jobid}/output/{OUTPUT_VERSION}/runs"
    from huggingface_hub import HfFileSystem
    fs = HfFileSystem()
    entries = fs.ls(root, detail=True)
    if not isinstance(entries, list) or len(entries) != 1:
        raise Hold("event directory ambiguous")
    entry = entries[0]
    if not isinstance(entry, dict):
        raise Hold("event listing malformed")
    fname = entry.get("name") or entry.get("path")
    if not isinstance(fname, str):
        raise Hold("event path missing")
    basename = fname.rsplit("/", 1)[-1]
    if not EVENT_NAME.fullmatch(basename) or jobid not in basename:
        raise Hold("event filename does not match private target")
    remote = root + "/" + basename
    before = fs.info(remote)
    if not isinstance(before, dict) or before.get("size") != EXPECTED_BYTES:
        raise Hold("event file size drift")
    with fs.open(remote, "rb") as f:
        buf = f.read(MAX_EVENT_BYTES + 1)
    if len(buf) != EXPECTED_BYTES:
        raise Hold("event file bytes size drift")
    after = fs.info(remote)
    if not isinstance(after, dict) or after.get("size") != EXPECTED_BYTES:
        raise Hold("event file changed")
    observed = parse_event_file(buf)
    return {
        "schema": SAFE_SCHEMA,
        "status": "EXISTING_PRIORITY_TENSORBOARD_SCALARS_PARSED__UPDATE_AND_EXPOSURE_HOLD",
        "single_owner_pinned_job": True,
        "hf_bucket_event_binary_read": True,
        "event_size_bytes": len(buf),
        **observed,
        "training_examples_or_other_logs_read": False,
        "private_job_id_or_raw_event_exported": False,
        "new_hf_job_started": False,
        "optimizer_step_called_directly_proven": False,
        "actual_weight_update_independently_proven": False,
        "historical_training_input_consumption_proven": False,
        "g1_clearance": "HOLD",
        "g2_clearance": "HOLD",
        "train_admitted": 0,
        "validation_admitted": 0,
        "teacher_admitted": 0,
        "expansion_allowed": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    base = Path.home() / ".storyforge-r58-private" / "round1_pilot_20261030"
    p.add_argument("--private-priority-ledger", type=Path,
                   default=base / "g1_hf_gpu_signal_priority_one_private.json")
    args = p.parse_args()
    try:
        print(json.dumps(run(args.private_priority_ledger), ensure_ascii=False, indent=2,
                         sort_keys=True))
        return 0
    except Exception:
        print(json.dumps({
            "schema": SAFE_SCHEMA,
            "status": "TENSORBOARD_SCALAR_READ_HOLD__UNAVAILABLE_OR_INVALID",
            "single_owner_pinned_job": True,
            "raw_log_or_private_id_exported": False,
            "new_hf_job_started": False,
            "g1_clearance": "HOLD",
            "g2_clearance": "HOLD",
            "train_admitted": 0,
            "validation_admitted": 0,
            "teacher_admitted": 0,
            "expansion_allowed": False,
        }, ensure_ascii=False, sort_keys=True, indent=2))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
