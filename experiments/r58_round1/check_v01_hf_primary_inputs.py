#!/usr/bin/env python3
"""R58 G1: read-only v0.1 three-Job primary input byte crosscheck.

Explicit Owner opt-in required before reading eight existing HF Bucket objects.
Only pinned PUBLIC Git v0.1 source JSONL is parsed locally to replay the
frozen prepare_sft transformation. Remote private files are *only* streamed
through SHA256; no remote text, logs, job commands or R50 are parsed/exported.
This never proves historical immutability, complete job coverage, or G1 release.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

BUCKET = "hf://buckets/adradar/storyforge-training"
SOURCE_PINS = {
    "train": ("3e64c9932ca43fefa8ecfb200085fe718581b6f9",
              "9a24f07befee9e701c587f4b154b0e780c29534abe3a0fa8b0c310511172a60f", 65),
    "validation": ("db0ae8b86038be1b372d547fdb2d6b0b7e33b54e",
                   "083a6f124abc414a0edf268d1a95788f738d55e7ecd229a78c67087991f46c36", 15),
}
PREPARE_GIT_BLOB_SHA = "2c60e69b0d288a3decfafdf2b07095c6dfed48a7"
RUN_DIRS = {
    "v01_rank32_smoke": ("runs/6ac73cabe7a0dae8a278117a", 3),
    "v01_rank64_capacity": ("baseline-runs/capacity/6ac74ce3df2184ac91ac8f43", 1),
    "v01_rank64_baseline": ("baseline-runs/baseline/6ac75bafdf2184ac91acb293", 9),
}
SCHEMA = "r58_g1_v01_three_job_primary_input_bytes_safe_v1"
MAX_SOURCE_BYTES = 4_000_000
MAX_REMOTE_BYTES = 6_000_000
CHUNK = 1024 * 1024

class Hold(ValueError):
    pass


def git_blob(repo: Path, oid: str) -> bytes:
    if not isinstance(oid, str) or re.fullmatch(r"[0-9a-f]{40}", oid) is None:
        raise Hold("invalid frozen Git blob")
    try:
        proc = subprocess.run(["git", "-C", str(repo), "cat-file", "blob", oid],
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                              check=False, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        raise Hold("frozen Git blob unavailable")
    if proc.returncode or not 0 < len(proc.stdout) <= MAX_SOURCE_BYTES:
        raise Hold("Git source invalid or too large")
    return proc.stdout


def replay_prepare_sft(public_source_bytes: bytes, expected_sha: str, rows: int) -> bytes:
    """Exactly reproduce scripts/prepare_sft.py (historical pinned blob).

    This parses only PUBLIC, already Git-tracked v0.1 data locally; it does not
    parse the remote Bucket bytes or any private R50 contents.
    """
    if hashlib.sha256(public_source_bytes).hexdigest() != expected_sha:
        raise Hold("public source SHA256 mismatch")
    lines = public_source_bytes.splitlines()
    if len(lines) != rows or any(not line.strip() for line in lines):
        raise Hold("public source row count mismatch")
    out = []
    for line in lines:
        try:
            item = json.loads(line)
            messages = item["messages"]
            if (not isinstance(messages, list) or len(messages) < 3
                or messages[-1]["role"] != "assistant" or messages[-2]["role"] != "user"):
                raise Hold("public source role contract mismatch")
            clean=[]
            for i,m in enumerate(messages):
                x={"role":m["role"],"content":m["content"]}
                if x["role"] == "assistant":
                    x["loss"] = (i == len(messages)-1)
                clean.append(x)
            out.append(json.dumps({"messages":clean},ensure_ascii=False)+"\n")
        except (TypeError, ValueError, KeyError, IndexError, UnicodeError) as exc:
            raise Hold("public source compilation failed") from None
    payload = "".join(out).encode("utf-8")
    if not 0 < len(payload) <= MAX_REMOTE_BYTES:
        raise Hold("compiled v0.1 payload size invalid")
    return payload


def hash_binary(file) -> tuple[str,int,int]:
    hasher=hashlib.sha256()
    nbytes=0;nl=0;last=b""
    while True:
        chunk=file.read(CHUNK)
        if type(chunk) is not bytes:
            raise Hold("nonbinary remote stream")
        if not chunk:break
        nbytes += len(chunk)
        if nbytes>MAX_REMOTE_BYTES:raise Hold("remote file too large")
        nl+=chunk.count(b"\n")
        last=chunk[-1:]
        hasher.update(chunk)
    if not nbytes:raise Hold("empty remote stream")
    return hasher.hexdigest(),nbytes,nl+int(last!=b"\n")


def verify_remote(fs, expected:dict[str,tuple[str,str,int]]) -> dict:
    """The ONLY remote reads are two shared + six per-Job predeclared files."""
    if set(expected) != {"train", "validation"}:
        raise Hold("source key mismatch")
    for split,(source_sha, compiled_sha,rows) in expected.items():
        if (rows != SOURCE_PINS[split][2] or
            source_sha != SOURCE_PINS[split][1] or
            not isinstance(compiled_sha,str) or re.fullmatch(r"[a-f0-9]{64}",compiled_sha) is None):
            raise Hold("Git-derived target contract mismatch")
    checks=0
    for split in ("train", "validation"):
        uri=f"{BUCKET}/datasets/v0.3/{split}.jsonl"
        with fs.open(uri,"rb") as f: sha,_,rows=hash_binary(f)
        if sha != expected[split][0] or rows != expected[split][2]:
            raise Hold("shared v0.1 Bucket bytes mismatch")
        checks+=1
    for role,(prefix,_steps) in RUN_DIRS.items():
        for split in ("train","validation"):
            uri=f"{BUCKET}/{prefix}/{split}.jsonl"
            with fs.open(uri,"rb") as f: sha,_,rows=hash_binary(f)
            if sha != expected[split][1] or rows != expected[split][2]:
                raise Hold("v0.1 Job-specific compiled input mismatch")
            checks+=1
    if checks!=8:raise Hold("remote object count mismatch")
    return {
        "schema":SCHEMA,
        "status":"R58_G1_V01_THREE_JOB_CURRENT_REMOTE_INPUT_BYTES_MATCH_GIT_REPLAY__HISTORY_AND_OTHER_HOLD",
        "owner_opt_in_private_v01_bucket_byte_read":True,
        "frozen_prepare_sft_git_blob_verified":True,
        "shared_v01_source_bucket_objects_verified":2,
        "v01_known_parameter_update_jobs_with_compiled_inputs_verified":3,
        "job_specific_compiled_input_bucket_objects_verified":6,
        "hf_bucket_objects_read":checks,
        "v01_train_rows_per_job":65,
        "v01_validation_rows_per_job":15,
        "v01_known_job_input_split_placements_verified":240,
        "known_jobs_are_smoke_capacity_baseline":True,
        "derived_compiled_train_sha256":expected["train"][1],
        "derived_compiled_validation_sha256":expected["validation"][1],
        "current_bucket_equality_proves_historical_job_read_these_bytes":False,
        "historical_bucket_immutability_proven":False,
        "every_training_example_received_gradients_proven":False,
        "other_hf_jobs_reviewed":False,
        "r50_protected_content_absence_proven":False,
        "private_bucket_files_decoded_or_logged":False,
        "private_world_uuids_or_remote_uris_exported":False,
        "new_hf_job_started":False,
        "all_actual_sft_runs_and_input_sources_proven_complete":False,
        "source_registry_complete":False,
        "g1_clearance":"HOLD",
        "train_admitted":0,"validation_admitted":0,"teacher_admitted":0,
        "expansion_allowed":False,
    }


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root",type=Path,required=True)
    parser.add_argument("--allow-read-only-private-v01-input-bytes",action="store_true")
    args=parser.parse_args(argv)
    if not args.allow_read_only_private_v01_input_bytes:
        print("R58_G1_V01_PRIMARY: HOLD (explicit Owner opt-in required)",file=sys.stderr)
        return 42
    try:
        if not args.repo_root.is_dir() or args.repo_root.is_symlink():
            raise Hold("repository unavailable")
        # Immutable historical compiler identity was verified in both the
        # original Smoke and Baseline Git revisions. Do not execute this blob.
        prepare=git_blob(args.repo_root,PREPARE_GIT_BLOB_SHA)
        if b"def convert(source: Path, dest: Path)" not in prepare:
            raise Hold("historical compiler mismatch")
        expected={}
        for split, (git_sha,sha,n) in SOURCE_PINS.items():
            public_source=git_blob(args.repo_root,git_sha)
            compiled=replay_prepare_sft(public_source,sha,n)
            expected[split]=(sha,hashlib.sha256(compiled).hexdigest(),n)
        from huggingface_hub import HfFileSystem
        safe=verify_remote(HfFileSystem(),expected)
        print(json.dumps(safe,ensure_ascii=False,indent=2,sort_keys=True))
        return 0
    except Exception:
        # Do not emit exception messages: remote providers may embed secrets.
        print("R58_G1_V01_PRIMARY: HOLD (frozen Git or remote Bucket source invalid/unavailable)",file=sys.stderr)
        return 42

if __name__=="__main__":raise SystemExit(main())
