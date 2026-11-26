#!/usr/bin/env python3
"""R58 G1: verify GitHub's documented historical training inputs, offline.

Only reads immutable Git blobs in the existing repository. The original
v0.1 JSONL is scanned for structural identity tokens, never JSON-decoded.
No access to private R56/R57/R58 ledgers, R50, HF, GPUs, or source prose output.
An accepted Git receipt is not a fresh attestation of actual remote input bytes.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

MANIFEST = "docs/evidence/R58_G1_GITHUB_HISTORICAL_TRAINING_SOURCES_SAFE_20261031.json"
SCHEMA = "r58_g1_github_historical_training_sources_safe_v1"
PINS = {
    "data/compiled/v0.3/train.jsonl": "3e64c9932ca43fefa8ecfb200085fe718581b6f9",
    "data/compiled/v0.3/validation.jsonl": "db0ae8b86038be1b372d547fdb2d6b0b7e33b54e",
    "data/compiled/v0.3/SHA256SUMS.txt": "18bb89497f492dc1a485cf90e9987eeb5c87c87f",
    "docs/evidence/V02_R46_GPU_TRAINING_ACCEPTANCE_20261014.json": "788701515f8f7c7afc840ace7ef7a8ba273493cb",
    "docs/evidence/V03_R53_R46_PRIMARY_EXPORT_OWNER_RECEIPT_VERIFIED_20261021.md": "ee3b0257dbe1f78f5458698bfe249264ac611c01",
    "docs/evidence/V03_R53_FORMAL_PRIVATE_31_9_RELEASE_OWNER_RECEIPT_ACCEPTED_20261021.md": "c3cf7613351448161c62d9ca5751c6d12bc050bb",
    "docs/evidence/GPU_SMOKE_20261008.md": "bd45d6f1cde67af6d16264d86ca364f31d70d797",
    "docs/evidence/BASELINE_SFT_V01_20261008.md": "8d6d1883abae031dbb881b0e742503ca0bf4b11c",
    "docs/HF_RUN_REGISTRY.md": "5a5c1ed11bf30bd763480b7c17ac366579e64dc0",
    "scripts/v03_r54_gpu_runner.py": "02c68be863dd95650b1f69022eb2420ebbe4d2c2",
    "configs/qwen38-27b-qlora-smoke.yaml": "d300706b0a33a23dd436d87aeb1d7a4fd12c7b18",
}
SPLITS = {
    "V01_TRAIN": (65, "9a24f07befee9e701c587f4b154b0e780c29534abe3a0fa8b0c310511172a60f"),
    "V01_VALIDATION": (15, "083a6f124abc414a0edf268d1a95788f738d55e7ecd229a78c67087991f46c36"),
    "R46_TRAIN": (49, "a028bf9fb28b12b4a3fa352d6a60281bd9e1ef5773ebfdfecc7ac80eb2cba517"),
    "R46_VALIDATION": (15, "cc8d647471423f4969149f8cabdea980aad15d8bd4424d9dd98da3313c639f3c"),
    "R54_TRAIN": (31, "d0425c54b534307047457d05e6890b50076ad2d23ce9ab3d52f94d1a3db585a7"),
    "R54_VALIDATION": (9, "b5ea4075419ce02a1340f6ece875068746918ce1d4c6d72ee2f799b3fe58754d"),
}
JOBS = {
    "v01_rank32_smoke": ("6ac73cabe7a0dae8a278117a", 3, "v0.1"),
    "v01_rank64_capacity": ("6ac74ce3df2184ac91ac8f43", 1, "v0.1"),
    "v01_rank64_baseline": ("6ac75bafdf2184ac91acb293", 9, "v0.1"),
    "r46_exploratory_sft": ("6acf29e4c66288145223871b", 7, "R46"),
    "r54_v2_sft": ("6ad8e60f5275124786e27d21", 16, "R54"),
}
UID = re.compile(rb"^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$")
STORY_TOKEN = re.compile(rb'"story_id"\s*:\s*"([0-9a-fA-F-]{36})"')
META_TOKEN = re.compile(rb'"metadata"\s*:\s*\{')
SAMPLE_TOKEN = re.compile(rb'"id"\s*:\s*"(sample-[0-9]{6})"')

class Hold(ValueError):
    pass

def read_blob(repo: Path, sha: str) -> bytes:
    if not isinstance(sha, str) or re.fullmatch("[a-f0-9]{40}", sha) is None:
        raise Hold("invalid immutable source SHA")
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "cat-file", "blob", sha],
            capture_output=True, check=False, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise Hold("Git blob unavailable")
    if proc.returncode or not 0 < len(proc.stdout) <= 4_000_000:
        raise Hold("source blob missing or oversized")
    return proc.stdout

def v01_worlds(blob: bytes, n: int, expected_sha: str) -> Counter:
    if hashlib.sha256(blob).hexdigest() != expected_sha:
        raise Hold("v0.1 SHA256 mismatch")
    rows = blob.splitlines()
    if len(rows) != n or any(not row.strip() for row in rows):
        raise Hold("v0.1 split row-count mismatch")
    counts, samples = Counter(), set()
    for raw in rows:
        uuids = STORY_TOKEN.findall(raw)
        ids = SAMPLE_TOKEN.findall(raw)
        if len(uuids) != 1 or len(ids) != 1 or len(META_TOKEN.findall(raw)) != 1:
            raise Hold("ambiguous v0.1 structural metadata")
        uid = uuids[0].lower()
        if UID.fullmatch(uid) is None or ids[0] in samples:
            raise Hold("malformed world identity or duplicate sample")
        samples.add(ids[0])
        counts[uid] += 1
    return counts

def r54_expected(source: str):
    """Only AST literal_eval on an immutable code blob. NEVER execute code."""
    try:
        nodes = ast.parse(source).body
    except SyntaxError:
        raise Hold("R54 runner invalid")
    candidates = []
    for node in nodes:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "EXPECTED" for t in node.targets
        ):
            try:
                candidates.append(ast.literal_eval(node.value))
            except (ValueError, TypeError, RecursionError):
                raise Hold("nonliteral R54 runner contract")
    if len(candidates) != 1 or not isinstance(candidates[0], dict):
        raise Hold("R54 runner contract absent/ambiguous")
    return candidates[0]

def validate_ledger(m: dict) -> None:
    if (not isinstance(m, dict)
        or m.get("schema") != SCHEMA
        or m.get("status") != "SIX_KNOWN_FROZEN_SPLITS_INDEXED__PRIMARY_REMOTE_AND_ALL_RUNS_HOLD"
        or m.get("git_sources") != PINS
        or m.get("g1_clearance") != "HOLD"
        or m.get("expansion_allowed") is not False
        or m.get("source_registry_complete") is not False
        or m.get("all_actual_sft_runs_and_input_sources_proven_complete") is not False
        or m.get("r50_protected_content_accessed") is not False
        or m.get("known_unique_world_uuids_recomputed_from_public_sources") is not False
        or any(m.get(k) != 0 for k in ("train_admitted", "validation_admitted", "teacher_admitted"))
    ):
        raise Hold("source ledger gate or Git pin mismatch")
    rows = m.get("splits")
    if not isinstance(rows, list) or len(rows) != 6:
        raise Hold("six split entries required")
    index = {x.get("key"): x for x in rows if isinstance(x, dict)}
    if len(index) != 6 or set(index) != set(SPLITS):
        raise Hold("split entry missing or duplicated")
    for key, (n, digest) in SPLITS.items():
        row = index[key]
        name, suffix = key.split("_", 1)
        group = {"V01":"v0.1", "R46":"R46", "R54":"R54"}[name]
        path = f"data/compiled/v0.3/{suffix.lower()}.jsonl" if name == "V01" else None
        level = {"V01":"GIT_CONTENT_AND_SHA256",
                 "R46":"GIT_RECEIPT_PLUS_OWNER_REMOTE_INPUT_ATTESTATION",
                 "R54":"GIT_PINNED_PRIVATE_RELEASE_AND_RUNNER_CONTRACT"}[name]
        if (row.get("run") != group or row.get("split") != suffix.lower()
            or type(row.get("rows")) is not int or row["rows"] != n
            or row.get("compiled_payload_sha256") != digest
            or row.get("public_evidence_level") != level
            or row.get("git_data_path") != path
            or row.get("git_data_blob_sha") != (PINS[path] if path else None)):
            raise Hold("split provenance drift")
    if (m.get("known_train_split_placements"), m.get("known_validation_split_placements"),
        m.get("known_total_split_placements"),
        m.get("known_unique_world_uuids_owner_private_reconciliation_reported")) != (145,39,184,27):
        raise Hold("aggregate source count drift")
    items=m.get("known_parameter_update_jobs")
    if not isinstance(items,list) or len(items)!=5:
        raise Hold("five known update jobs required")
    jobs={x.get("role"):x for x in items if isinstance(x,dict)}
    if len(jobs)!=5 or set(jobs)!=set(JOBS):
        raise Hold("Job roster mismatch")
    for role,(jid,steps,run) in JOBS.items():
        job=jobs[role]
        if (job.get("job_id")!=jid or job.get("reported_optimizer_steps")!=steps
            or job.get("declared_split_source")!=run
            or job.get("runtime_input_bytes_independently_rehashed_here") is not False):
            raise Hold("Job source evidence drift")

def verify(m: dict, blobs: dict[str,bytes]) -> dict:
    validate_ledger(m)
    if set(blobs)!=set(PINS):
        raise Hold("missing pinned source objects")
    sums=blobs["data/compiled/v0.3/SHA256SUMS.txt"].decode("utf-8").splitlines()
    sum_map={}
    for line in sums:
        match=re.fullmatch(r"([a-f0-9]{64})  (data/compiled/v0\.3/[A-Za-z0-9._/-]+)",line)
        if not match or match[2] in sum_map:
            raise Hold("invalid v0.1 checksums")
        sum_map[match[2]]=match[1]
    if len(sum_map)!=5:
        raise Hold("incomplete v0.1 checksum list")
    worlds={}
    for key in ("V01_TRAIN","V01_VALIDATION"):
        path=f"data/compiled/v0.3/{key.split('_')[1].lower()}.jsonl"
        n,digest=SPLITS[key]
        if sum_map.get(path)!=digest:
            raise Hold("v0.1 original checksum mismatch")
        worlds[key]=v01_worlds(blobs[path],n,digest)
    if set(worlds["V01_TRAIN"]) & set(worlds["V01_VALIDATION"]):
        raise Hold("v0.1 world split collision")
    r46=json.loads(blobs["docs/evidence/V02_R46_GPU_TRAINING_ACCEPTANCE_20261014.json"])
    if (r46.get("status")!="EXPLORATORY_GPU_SFT_PASS_NOT_PROMOTED"
        or r46.get("hf_job_id")!=JOBS["r46_exploratory_sft"][0]
        or (r46.get("train_rows"),r46.get("validation_rows"))!=(49,15)
        or r46.get("compiled_train_sha256")!=SPLITS["R46_TRAIN"][1]
        or r46.get("compiled_validation_sha256")!=SPLITS["R46_VALIDATION"][1]
        or r46.get("training_finished") is not True):
        raise Hold("R46 acceptance record mismatch")
    receipt=blobs["docs/evidence/V03_R53_R46_PRIMARY_EXPORT_OWNER_RECEIPT_VERIFIED_20261021.md"].decode()
    if not all(x in receipt for x in ("49 frozen Train / 15 frozen Validation",
                                     SPLITS["R46_TRAIN"][1],SPLITS["R46_VALIDATION"][1])):
        raise Hold("R46 original-input receipt mismatch")
    runner=r54_expected(blobs["scripts/v03_r54_gpu_runner.py"].decode())
    if runner.get("train")!=(SPLITS["R54_TRAIN"][1],31) or runner.get("validation")!=(SPLITS["R54_VALIDATION"][1],9):
        raise Hold("R54 runner input SHA contract mismatch")
    release=blobs["docs/evidence/V03_R53_FORMAL_PRIVATE_31_9_RELEASE_OWNER_RECEIPT_ACCEPTED_20261021.md"].decode()
    if not all(x in release for x in (SPLITS["R54_TRAIN"][1],SPLITS["R54_VALIDATION"][1],
                                      "DATA_ONLY_RELEASE_APPROVED__GPU_NOT_AUTHORIZED")):
        raise Hold("R54 release receipt mismatch")
    smoke=blobs["docs/evidence/GPU_SMOKE_20261008.md"].decode()
    baseline=blobs["docs/evidence/BASELINE_SFT_V01_20261008.md"].decode()
    registry=blobs["docs/HF_RUN_REGISTRY.md"].decode()
    cfg=blobs["configs/qwen38-27b-qlora-smoke.yaml"].decode()
    if (JOBS["v01_rank32_smoke"][0] not in smoke
        or JOBS["v01_rank64_baseline"][0] not in baseline
        or any(jid not in registry for role,(jid,steps,run) in JOBS.items() if run=="v0.1")
        or "data/compiled/v0.3/train.jsonl" not in cfg
        or "data/compiled/v0.3/validation.jsonl" not in cfg):
        raise Hold("v0.1 source/job linkage mismatch")
    return {
        "schema":"r58_g1_github_historical_training_sources_verification_safe_v1",
        "status":"R58_G1_GITHUB_KNOWN_TRAINING_SOURCES_VERIFIED__REMOTE_AND_OTHER_HOLD",
        "pinned_git_source_objects_verified":len(PINS),
        "known_split_source_records_reconciled":184,
        "v01_compiled_data_sha256_verified":True,
        "v01_train_world_count":len(worlds["V01_TRAIN"]),
        "v01_validation_world_count":len(worlds["V01_VALIDATION"]),
        "v01_train_validation_world_overlap":0,
        "r46_report_receipt_hash_contract_verified":True,
        "r54_runner_release_hash_contract_verified":True,
        "five_known_parameter_update_jobs_documented":True,
        "remote_training_primary_input_bytes_rehashed_this_step":False,
        "all_actual_sft_runs_and_input_sources_proven_complete":False,
        "historical_other_job_classification_complete":False,
        "private_world_uuids_or_narratives_exported":False,
        "r50_protected_content_accessed":False,
        "source_registry_complete":False,
        "g1_clearance":"HOLD",
        "train_admitted":0,"validation_admitted":0,"teacher_admitted":0,
        "expansion_allowed":False,
    }

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root",type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        path=args.repo_root/MANIFEST
        if path.is_symlink() or not path.is_file() or path.stat().st_size>40000:
            raise Hold("source ledger missing or unsafe")
        ledger=json.loads(path.read_bytes())
        blobs={path:read_blob(args.repo_root,sha) for path,sha in PINS.items()}
        print(json.dumps(verify(ledger,blobs),ensure_ascii=False,sort_keys=True,indent=2))
        return 0
    except Exception:
        print("R58_G1_GITHUB_SOURCES: HOLD (frozen Git inputs missing or inconsistent)",file=sys.stderr)
        return 42

if __name__=="__main__":
    raise SystemExit(main())
