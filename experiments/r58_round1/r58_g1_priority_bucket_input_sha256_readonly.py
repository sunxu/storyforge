#!/usr/bin/env python3
"""R58 G1: one PRIVATE-priority CANCELED HF Job, current Bucket input byte fingerprints.

Read only the two exact HF Bucket files train.jsonl and validation.jsonl;
stream SHA256 without parsing, displaying, saving or uploading dataset rows.
Existing PRIVATE priority metadata supplies the Job identity.
Stores computed digests ONLY in an exclusive 0600 PRIVATE local receipt,
and prints only a SAFE pin-match summary. Never starts HF jobs, opens
logging/commands/environment, or claims the inputs were consumed historically.

Requires local `huggingface_hub` with Storage Bucket support and HF auth.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

ROOT = "hf://buckets/adradar/storyforge-training/runs"
PRIORITY_SCHEMA = "r58_round1_g1_gpu_signal_priority_case_private_v1"
PRIVATE_SCHEMA = "r58_g1_one_job_current_bucket_input_hashes_private_v1"
SAFE_SCHEMA = "r58_g1_one_job_current_bucket_input_hashes_safe_v1"
MAX_LEDGER_BYTES = 12_000
CHUNK = 256 * 1024
FILES = {
    "train": ("train.jsonl", 2_013_373),
    "validation": ("validation.jsonl", 381_363),
}
# Published frozen SHA256 references from
# docs/evidence/R58_G1_GITHUB_HISTORICAL_TRAINING_SOURCES_SAFE_20261031.json
# and R58_G1_KNOWN_FIVE_JOB_CURRENT_PRIMARY_INPUTS_CROSSCHECK_SAFE_20261031.json.
# These hashes are public evidence pins, NOT hashes of this target Job's files.
PINS = {
    "train": {
        "V01_GIT_SOURCE": "9a24f07befee9e701c587f4b154b0e780c29534abe3a0fa8b0c310511172a60f",
        "V01_DERIVED_COMPILED": "68a535fcb0fd9249c630d31e2623a9708f700b9ece27388f4a34fd5166ab84af",
        "R46": "a028bf9fb28b12b4a3fa352d6a60281bd9e1ef5773ebfdfecc7ac80eb2cba517",
        "R54": "d0425c54b534307047457d05e6890b50076ad2d23ce9ab3d52f94d1a3db585a7",
    },
    "validation": {
        "V01_GIT_SOURCE": "083a6f124abc414a0edf268d1a95788f738d55e7ecd229a78c67087991f46c36",
        "V01_DERIVED_COMPILED": "138f3cbff7914337db2e2d438f335573c5c4d770f0e390186e4bc9f70b085557",
        "R46": "cc8d647471423f4969149f8cabdea980aad15d8bd4424d9dd98da3313c639f3c",
        "R54": "b5ea4075419ce02a1340f6ece875068746918ce1d4c6d72ee2f799b3fe58754d",
    },
}
RE_JOB = re.compile(r"[a-f0-9]{24}\Z")
RE_SHA = re.compile(r"[a-f0-9]{64}\Z")


class Hold(Exception):
    pass


def private_paths(ledger: Path, output: Path) -> None:
    root = Path.home() / ".storyforge-r58-private"
    for p in (ledger, output):
        if not p.is_absolute() or not p.is_relative_to(root):
            raise Hold("private path outside local root")
        parts = p.relative_to(root).parts
        cur = root
        for part in parts[:-1]:
            cur = cur / part
            if cur.is_symlink():
                raise Hold("symlink in private path")
        if p.is_symlink():
            raise Hold("private path is symlink")
    if ledger == output:
        raise Hold("private input-output collision")


def load_priority(ledger: Path) -> dict:
    fd = os.open(str(ledger), os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as f:
        st = os.fstat(f.fileno())
        if (not stat.S_ISREG(st.st_mode) or (st.st_mode & 0o077) != 0
                or not 0 < st.st_size <= MAX_LEDGER_BYTES):
            raise Hold("invalid private ledger")
        raw = f.read(MAX_LEDGER_BYTES + 1)
    if len(raw) > MAX_LEDGER_BYTES:
        raise Hold("oversized private ledger")
    try:
        obj = json.loads(raw)
    except (ValueError, UnicodeError) as e:
        raise Hold("invalid ledger JSON") from e
    if not isinstance(obj, dict) or obj.get("schema") != PRIORITY_SCHEMA:
        raise Hold("wrong ledger schema")
    jobid = obj.get("hf_job_id_PRIVATE")
    logsha = obj.get("prior_gpu_log_sha256_PRIVATE")
    if (not isinstance(jobid, str) or not RE_JOB.fullmatch(jobid)
            or not isinstance(logsha, str) or not RE_SHA.fullmatch(logsha)
            or obj.get("namespace") != "adradar"
            or obj.get("stage") != "CANCELED"
            or obj.get("status") != "ONE_POTENTIAL_LOG_INDICATOR__PROOF_NOT_ESTABLISHED"
            or obj.get("indicator_classes") != ["TRAINING_LOSS_GRAD_TELEMETRY"]
            or obj.get("update_proof_status") != "PENDING_PRIMARY_RUN_ARTIFACT"
            or obj.get("training_input_sha256_status") != "NOT_VERIFIED"
            or obj.get("train_validation_usage_status") != "NOT_VERIFIED"
            or obj.get("g1_clearance") != "HOLD"
            or obj.get("expansion_allowed") is not False):
        raise Hold("private priority identity or scope drift")
    return obj


def meta_size(fs, remote: str) -> tuple[int, object]:
    info = fs.info(remote)
    if not isinstance(info, dict) or info.get("type") != "file":
        raise Hold("remote input is not a file")
    size = info.get("size")
    if type(size) is not int or size <= 0:
        raise Hold("invalid remote size")
    mtime = info.get("last_modified", info.get("updated_at"))
    return size, str(mtime) if mtime is not None else None


def fingerprint(fs, remote: str, expected_size: int) -> tuple[str, int, bool]:
    before_size, before_time = meta_size(fs, remote)
    if before_size != expected_size:
        raise Hold("bucket input size differs from pinned listing")
    digest = hashlib.sha256()
    total = 0
    with fs.open(remote, "rb") as f:
        while True:
            data = f.read(CHUNK)
            if not data:
                break
            if not isinstance(data, bytes):
                raise Hold("not byte stream")
            total += len(data)
            if total > expected_size:
                raise Hold("remote input grew")
            digest.update(data)
    after_size, after_time = meta_size(fs, remote)
    if total != expected_size or after_size != expected_size:
        raise Hold("input length changed during read")
    if before_time is not None and after_time is not None and before_time != after_time:
        raise Hold("input mtime changed during read")
    return digest.hexdigest(), total, bool(before_time is not None and after_time is not None)


def write_private(path: Path, obj: dict) -> None:
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, sort_keys=True, indent=2)
            f.write("\n")
    except BaseException:
        try:
            path.unlink(missing_ok=True)
        finally:
            raise


def run(ledger: Path, output: Path) -> dict:
    private_paths(ledger, output)
    if os.path.lexists(str(output)):
        raise Hold("private output exists, no overwrite")
    priority = load_priority(ledger)
    from huggingface_hub import HfFileSystem
    fs = HfFileSystem()
    values: dict[str, dict] = {}
    safe_matches: dict[str, list[str]] = {}
    for split, (name, size) in FILES.items():
        remote = f"{ROOT}/{priority['hf_job_id_PRIVATE']}/{name}"
        digest, nbytes, time_check = fingerprint(fs, remote, size)
        values[split] = {"sha256_PRIVATE": digest, "size_bytes": nbytes,
                         "metadata_mtime_consistent_when_available": time_check}
        safe_matches[split] = sorted(label for label, pin in PINS[split].items() if pin == digest)
    private = {
        "schema": PRIVATE_SCHEMA,
        "status": "CURRENT_TARGET_BUCKET_INPUTS_HASHED__NOT_HISTORICAL_CONSUMPTION",
        "hf_job_id_PRIVATE": priority["hf_job_id_PRIVATE"],
        "namespace": "adradar",
        "prior_gpu_log_sha256_PRIVATE": priority["prior_gpu_log_sha256_PRIVATE"],
        "hashes_PRIVATE": values,
        "matches_public_pins": safe_matches,
        "historical_job_consumption_proven": False,
        "bucket_history_immutable": False,
        "g1_clearance": "HOLD",
    }
    write_private(output, private)
    return {
        "schema": SAFE_SCHEMA,
        "status": "CURRENT_TARGET_BUCKET_INPUTS_SHA256_VERIFIED__HISTORICAL_EXPOSURE_HOLD",
        "target_jobs_checked": 1,
        "provider_identity_bound_to_private_priority_ledger": True,
        "train_bytes_sha256_computed": True,
        "validation_bytes_sha256_computed": True,
        "train_file_size_bytes": values["train"]["size_bytes"],
        "validation_file_size_bytes": values["validation"]["size_bytes"],
        "matches_public_frozen_hashes": safe_matches,
        "private_digest_receipt_written": True,
        "job_id_or_private_digests_exported": False,
        "input_jsonl_decoded_or_rows_parsed": False,
        "trainer_state_or_optimizer_artifacts_read": False,
        "job_command_logs_environment_read": False,
        "hf_job_started": False,
        "current_bucket_bytes_equal_historical_consumed_bytes_proven": False,
        "actual_optimizer_update_proven": False,
        "source_registry_complete": False,
        "g1_clearance": "HOLD",
        "g2_clearance": "HOLD",
        "train_admitted": 0,
        "validation_admitted": 0,
        "teacher_admitted": 0,
        "expansion_allowed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    base = Path.home() / ".storyforge-r58-private" / "round1_pilot_20261030"
    parser.add_argument("--private-priority-ledger", type=Path,
                        default=base / "g1_hf_gpu_signal_priority_one_private.json")
    parser.add_argument("--private-output", type=Path,
                        default=base / "g1_priority_bucket_input_hashes_PRIVATE_20261101.json")
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.private_priority_ledger, args.private_output),
                         ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except Exception:
        # Fail closed, no raw paths, private data or API exception exported.
        print(json.dumps({"schema": SAFE_SCHEMA,
                          "status": "INPUT_HASH_PROBE_FAILED__G1_HOLD",
                          "target_jobs_checked": 1, "hf_job_started": False,
                          "private_digest_or_job_id_exported": False,
                          "g1_clearance": "HOLD", "g2_clearance": "HOLD",
                          "train_admitted": 0, "validation_admitted": 0,
                          "teacher_admitted": 0, "expansion_allowed": False},
                         ensure_ascii=False, sort_keys=True, indent=2))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
