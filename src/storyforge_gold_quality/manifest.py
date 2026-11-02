from __future__ import annotations

from collections import Counter, defaultdict
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import uuid

SCHEMA = "storyforge_gold_quality_manifest_event_v1"
EVENT_TYPES = {"SOURCE_FREEZE", "LEGACY_SELECTION_EVIDENCE", "LEGACY_REVIEW",
               "SOURCE_METADATA", "TRAINING_EXPOSURE_AGGREGATE", "TRAINING_EXPOSURE_ROW",
               "WORLD_IDENTITY_REVIEW", "INCREMENTAL_REVIEW", "BLIND_REVIEW",
               "ADJUDICATION", "STRUCTURE_VALIDATION", "TOKEN_PREFLIGHT", "FREEZE", "EXCLUSION"}
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class ManifestError(ValueError):
    pass


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ManifestError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def validate_event(event):
    required = {"schema", "event_id", "batch_id", "event_type", "recorded_at", "payload"}
    if not isinstance(event, dict) or not required.issubset(event):
        raise ManifestError("EVENT_SCHEMA_INVALID")
    if event["schema"] != SCHEMA or event["event_type"] not in EVENT_TYPES:
        raise ManifestError("EVENT_SCHEMA_INVALID")
    if not isinstance(event["payload"], dict):
        raise ManifestError("EVENT_PAYLOAD_INVALID")
    digest = event["payload"].get("target_sha256")
    if digest is not None and (not isinstance(digest, str) or not HEX64.fullmatch(digest)):
        raise ManifestError("TARGET_HASH_INVALID")
    return event


def load_events(path):
    if path.is_symlink() or not path.is_file():
        raise ManifestError("MANIFEST_NOT_REGULAR_FILE")
    events = []
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                raise ManifestError("MANIFEST_BLANK_LINE")
            events.append(validate_event(json.loads(line, object_pairs_hook=_pairs)))
    return events


def make_event(batch_id, event_type, payload, recorded_at):
    return {"schema": SCHEMA, "event_id": str(uuid.uuid4()), "batch_id": batch_id,
            "event_type": event_type, "recorded_at": recorded_at, "payload": payload}


def append_events(path, events, repo_root):
    if not events:
        raise ManifestError("NO_EVENTS_TO_APPEND")
    parent = path.parent.absolute()
    repo = repo_root.resolve(strict=True)
    try:
        parent.relative_to(repo)
    except ValueError:
        pass
    else:
        raise ManifestError("PRIVATE_MANIFEST_MUST_BE_OUTSIDE_REPOSITORY")
    parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    if any(p.is_symlink() for p in (parent, *parent.parents)):
        raise ManifestError("PRIVATE_PATH_SYMLINK")
    if parent.resolve().stat().st_mode & 0o077:
        raise ManifestError("PRIVATE_PARENT_PERMISSIONS_TOO_OPEN")
    checked = [validate_event(x) for x in events]
    ids = [x["event_id"] for x in checked]
    if len(ids) != len(set(ids)):
        raise ManifestError("DUPLICATE_EVENT_ID")
    flags = os.O_RDWR | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ManifestError("MANIFEST_NOT_REGULAR_FILE")
        os.fchmod(fd, 0o600)
        os.lseek(fd, 0, os.SEEK_SET)
        raw = b""
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            raw += chunk
        old = [validate_event(json.loads(line, object_pairs_hook=_pairs))
               for line in raw.decode("utf-8").splitlines() if line]
        old_ids = {x["event_id"] for x in old}
        if old_ids.intersection(ids):
            raise ManifestError("EVENT_ID_ALREADY_EXISTS")
        targets = {}
        for event in old + checked:
            payload = event["payload"]
            case = payload.get("case_id") or payload.get("case_ref")
            digest = payload.get("target_sha256")
            if case and digest:
                key = (event["batch_id"], case)
                prior = targets.setdefault(key, digest)
                if prior != digest:
                    raise ManifestError("CASE_TARGET_HASH_CHANGED")
        for event in checked:
            data = (json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
            view = memoryview(data)
            while view:
                count = os.write(fd, view)
                if count <= 0:
                    raise ManifestError("MANIFEST_APPEND_FAILED")
                view = view[count:]
        os.fsync(fd)
    finally:
        os.close(fd)
    return len(checked)


def validate_manifest(events):
    if len({x["event_id"] for x in events}) != len(events):
        raise ManifestError("DUPLICATE_EVENT_ID")
    by_batch, cases, target_pins = defaultdict(Counter), defaultdict(set), {}
    for event in events:
        by_batch[event["batch_id"]][event["event_type"]] += 1
        payload = event["payload"]
        case = payload.get("case_id") or payload.get("case_ref")
        if case:
            cases[event["batch_id"]].add(case)
            digest = payload.get("target_sha256")
            if digest:
                key = (event["batch_id"], case)
                if key in target_pins and target_pins[key] != digest:
                    raise ManifestError("CASE_TARGET_HASH_CHANGED")
                target_pins[key] = digest
    return {"valid": True, "event_count": len(events), "batch_count": len(by_batch),
            "case_counts": {k: len(v) for k, v in sorted(cases.items())},
            "event_counts": {k: dict(sorted(v.items())) for k, v in sorted(by_batch.items())}}


def safe_report(events):
    summary = validate_manifest(events)
    decisions, tiers = Counter(), Counter()
    for event in events:
        payload = event["payload"]
        if payload.get("decision"):
            decisions[payload["decision"]] += 1
        if payload.get("evidence_tier"):
            tiers[payload["evidence_tier"]] += 1
    return {"schema": "storyforge_gold_quality_safe_aggregate_v1",
            "status": "MANIFEST_VALID__ADMISSION_NOT_IMPLIED",
            **summary, "decision_counts": dict(sorted(decisions.items())),
            "exposure_evidence_tiers": dict(sorted(tiers.items())),
            "quality_v1_admitted": 0, "training_authorized": False,
            "gpu_started": False, "r50_accessed": False, "private_values_emitted": False}
