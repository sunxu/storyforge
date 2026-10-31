#!/usr/bin/env python3
"""R58 G1: strictly scoped, read-only HF Bucket trainer-artifact presence probe.

No HF Job launches, no raw logs/commands/env, no training data reads, no private IDs
or hashes in stdout, no filesystem writes.  Uses the existing sealed priority ledger
and only probes known job-ID-specific output prefixes.  Always G1 HOLD.

Requires existing local StoryForge R58 checkout + huggingface_hub credentials.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SOURCE_LAYOUTS = (
    "runs/{job_id}",
    "baseline-runs/capacity/{job_id}",
    "baseline-runs/baseline/{job_id}",
)
BUCKET = "hf://buckets/adradar/storyforge-training"
MAX_LIST_ITEMS = 300
MAX_DIRS = 24
MAX_READ_BYTES = 131072
CHECKPOINT_DIR_RE = re.compile(r"checkpoint-[1-9][0-9]*\Z")
PRIVATE_NAME = "g1_hf_gpu_signal_priority_one_private.json"


def safe_result(**overrides):
    payload = {
        "schema": "r58_g1_one_canceled_job_trainer_artifact_presence_safe_v1",
        "status": "PRIMARY_TRAINER_ARTIFACT_SCOPED_PROBE__G1_HOLD",
        "job_count": 1,
        "job_id_and_secret_exported": False,
        "hf_job_started": False,
        "hf_job_inspect_called": False,
        "command_arguments_environment_logs_read": False,
        "protected_stories_or_training_examples_read": False,
        "private_ledger_modified": False,
        "prefixes_checked": 0,
        "job_specific_prefix_accessible": False,
        "trainer_state_file_found": False,
        "trainer_state_parsed_from_existing_artifact": False,
        "positive_global_step_observed": False,
        "checkpoint_directory_found": False,
        "optimizer_file_metadata_found": False,
        "checkpoint_step_matches_trainer_state": False,
        "provider_authenticated_job_to_artifact_link": False,
        "runtime_optimizer_step_independently_proven": False,
        "historical_train_input_sha256_verified": False,
        "historical_validation_input_sha256_verified": False,
        "source_registry_complete": False,
        "g1_clearance": "HOLD",
        "g2_clearance": "HOLD",
        "train_admitted": 0,
        "validation_admitted": 0,
        "teacher_admitted": 0,
        "expansion_allowed": False,
    }
    payload.update(overrides)
    return payload


def basename(path: str) -> str:
    return path.rstrip("/").rsplit("/", 1)[-1]


def is_dir(row: dict) -> bool:
    return row.get("type") == "directory"


def scan_prefix(fs, prefix: str):
    """Only list selected job-specific output/checkpoint directories."""
    # HfFileSystem returns metadata names without the hf:// URI scheme.
    # Normalize once to avoid silently rejecting every returned row.
    prefix = prefix.removeprefix("hf://")
    dirs = [prefix]
    listed = 0
    visited = 0
    trainer_states = []
    checkpoints = set()
    optimizers = set()
    while dirs:
        d = dirs.pop(0)
        visited += 1
        if visited > MAX_DIRS:
            raise ValueError("bounded directory traversal limit")
        entries = fs.ls(d, detail=True, refresh=True)
        if not isinstance(entries, list):
            raise ValueError("unexpected bucket listing")
        listed += len(entries)
        if listed > MAX_LIST_ITEMS:
            raise ValueError("bounded listing limit")
        for row in entries:
            if not isinstance(row, dict) or not isinstance(row.get("name"), str):
                raise ValueError("unexpected bucket metadata")
            p = row["name"]
            if not (p.startswith(d.rstrip("/") + "/") and ".." not in p.split("/")):
                raise ValueError("unexpected prefix escape")
            name = basename(p)
            if is_dir(row):
                if CHECKPOINT_DIR_RE.fullmatch(name):
                    checkpoints.add(p)
                    dirs.append(p)
                elif d == prefix and name in {"output", "artifacts", "checkpoints"}:
                    dirs.append(p)
                elif d.startswith(prefix + "/") and d[len(prefix) + 1:].split("/")[0] in {"output", "artifacts", "checkpoints"}:
                    # Follow bounded run/checkpoint subfolders within the same Job,
                    # but never enter dataset, input, log, cache or secret trees.
                    if len(d[len(prefix) + 1:].split("/")) < 4 and name not in {
                        "data", "datasets", "input", "inputs", "logs", "cache", "secrets", "private"
                    }:
                        dirs.append(p)
                # No traversal into datasets or unrelated Job outputs.
            else:
                if name == "trainer_state.json":
                    trainer_states.append((p, row))
                elif (name == "optimizer.pt"
                      and isinstance(row.get("size"), int) and row["size"] > 0
                      and CHECKPOINT_DIR_RE.fullmatch(basename(p.rsplit("/", 1)[0]))):
                    optimizers.add(p.rsplit("/", 1)[0])
    return trainer_states, checkpoints, optimizers


def trainer_step(fs, name: str, metadata: dict):
    size = metadata.get("size")
    if not isinstance(size, int) or not (0 < size <= MAX_READ_BYTES):
        raise ValueError("trainer state absent or exceeds read limit")
    with fs.open(name, "rb") as f:
        raw = f.read(MAX_READ_BYTES + 1)
    if len(raw) > MAX_READ_BYTES or len(raw) != size:
        raise ValueError("trainer state read length mismatch")
    obj = json.loads(raw.decode("utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("invalid trainer state")
    # Never inspect log_history, args, commands, sample paths, or any other keys.
    step = obj.get("global_step")
    if type(step) is not int or step < 0:
        raise ValueError("invalid global step")
    return step


def run(args):
    repo = args.repo_root.resolve(strict=True)
    if not (repo / "skills/storyforge-roleplay-sft/v02/r58_existing_priority_receipt.py").is_file():
        raise ValueError("missing R58 checked-out source")
    ledger = args.private_priority_ledger
    # Reuse the established R58 fail-closed O_NOFOLLOW/private-ledger reader.
    sys.path.insert(0, str(repo / "experiments/r58_round1"))
    from inspect_hf_priority_job_metadata import read_priority  # noqa: PLC0415
    priority = read_priority(ledger)
    job_id = priority["hf_job_id_PRIVATE"]

    # Validate placeholders before any HF connection, so user never needs to
    # paste the actual private Job ID into command line or shell history.
    templates = list(SOURCE_LAYOUTS)
    if args.extra_prefix_template:
        template = args.extra_prefix_template
        if template.count("{job_id}") != 1 or template.startswith("/") or ".." in template.split("/"):
            raise ValueError("invalid optional job-scoped prefix template")
        templates.append(template)
    all_prefixes = []
    for template in templates:
        rendered = template.replace("{job_id}", job_id).strip("/")
        if not re.fullmatch(r"[a-zA-Z0-9_./-]+", rendered) or ".." in rendered.split("/"):
            raise ValueError("invalid prefix")
        if job_id not in rendered.split("/"):
            raise ValueError("prefix does not uniquely bind the priority Job")
        all_prefixes.append(BUCKET + "/" + rendered)

    from huggingface_hub import HfFileSystem  # noqa: PLC0415
    fs = HfFileSystem()
    checked = 0
    accessible = False
    states = []
    trainer_metadata_found = False
    checkpoint_found = False
    optimizer_found = False
    match_found = False
    for prefix in all_prefixes:
        checked += 1
        try:
            state_files, checkpoint_dirs, optimizer_dirs = scan_prefix(fs, prefix)
        except (OSError, ValueError, KeyError):
            # Not found, permission problems, or unsafe listing are *not* proof
            # of absence.  No remote error messages or paths are printed.
            continue
        accessible = True
        checkpoint_found |= bool(checkpoint_dirs)
        trainer_metadata_found |= bool(state_files)
        optimizer_found |= bool(optimizer_dirs)
        for filename, meta in state_files:
            try:
                step = trainer_step(fs, filename, meta)
                states.append(step)
                if step > 0:
                    match_found |= any(
                        basename(directory) == f"checkpoint-{step}"
                        for directory in checkpoint_dirs
                    )
            except (OSError, ValueError, TypeError, KeyError, UnicodeError):
                continue
    result = safe_result(
        prefixes_checked=checked,
        job_specific_prefix_accessible=accessible,
        trainer_state_file_found=trainer_metadata_found,
        trainer_state_parsed_from_existing_artifact=bool(states),
        positive_global_step_observed=any(x > 0 for x in states),
        checkpoint_directory_found=checkpoint_found,
        optimizer_file_metadata_found=optimizer_found,
        checkpoint_step_matches_trainer_state=match_found,
    )
    # None of these presence claims independently prove artifact ownership,
    # optimizer updates, or the historical train/validation input fingerprints.
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root", type=Path, required=True)
    p.add_argument("--private-priority-ledger", type=Path, required=True)
    p.add_argument("--extra-prefix-template", default=None,
                   help="optional job-scoped HF Bucket relative prefix with literal {job_id} placeholder")
    a = p.parse_args(argv)
    try:
        result = run(a)
        print(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False))
        return 0
    except Exception:
        print(json.dumps(safe_result(status="PRIVATE_OR_HF_SOURCE_UNAVAILABLE__G1_HOLD"),
                         sort_keys=True, indent=2, ensure_ascii=False))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
