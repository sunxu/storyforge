"""Mac-only minimal private Gold48 HF CPU Tokenizer stage, create-only.

Reuses the existing Gold48 draft validator and Common2 dependency closure.
Removes source Story IDs, owner mapping, and historical original replies from
the uploaded input. Preserves exactly 48 reconstructed_messages and hashes.
Does not submit, upload, tokenize, call HF, or touch frozen candidates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
from collections import Counter
from pathlib import Path

from r60_common2_wrapped_hf_stage import local_dependencies
from r60_p2_gold48_token_preflight_cpu import load_draft

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "storyforge_r60_gold48_hf_cpu_token_stage_private_v1"
INPUT_NAME = "GOLD48_HF_CPU_MINIMAL_INPUT_PRIVATE.json"
INPUT = "private/" + INPUT_NAME
MANIFEST = "SHA256_MANIFEST_PRIVATE.json"
RUN_RE = re.compile(r"r60-gold48-cpu-\d{8}T\d{6}Z-[a-f0-9]{12}\Z")
ENTRY = (
    "scripts/r60_p2_gold48_hf_cpu_worker.sh",
    "scripts/r60_p2_gold48_hf_cpu_worker.py",
    "scripts/r60_p2_gold48_token_preflight_cpu.py",
    "requirements/hf-cpu-tokenizer.lock",
)
EXTRA = ("src/storyforge_dataset/token_preflight.py",)
MAX_FILE_BYTES = 32 * 1024 * 1024


class Hold(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise Hold(reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def stage_files():
    return local_dependencies(entries=ENTRY, extras=EXTRA)


def minimally_staged(draft_file):
    draft_raw, original, _ = load_draft(draft_file)
    # Use a private, deterministic anon group label, never actual Story IDs.
    groups = {}
    rows = []
    counts = Counter()
    for i, row in enumerate(original):
        # Provenance has already been validated by load_draft().
        doc = json.loads(draft_raw)["cases_PRIVATE"][i]
        story = doc["story_id_PRIVATE"]
        if story not in groups:
            groups[story] = f"ANON-GROUP-{len(groups) + 1:02d}"
        group = groups[story]
        counts[group] += 1
        rows.append({
            "candidate_case_id_PRIVATE": doc["candidate_case_id_PRIVATE"],
            "story_id_PRIVATE": group,
            "source_revision_PRIVATE": doc["source_revision_PRIVATE"],
            "source_components_provenance": "EVALUATION_TIME_SNAPSHOT",
            "system_provenance": "EVALUATION_CONSTRUCTED_GENERIC_SYSTEM",
            "rules_provenance": "ONLY_AS_EXPRESSED_IN_PUBLIC_CARD_WORLD",
            "memory_provenance": doc["memory_provenance"],
            "historical_actual_sent_verified": False,
            "reconstructed_messages_sha256_PRIVATE":
                doc["reconstructed_messages_sha256_PRIVATE"],
            "history_prefix_sha256_PRIVATE":
                doc["history_prefix_sha256_PRIVATE"],
            "reconstructed_messages_PRIVATE": row,
        })
    require(len(rows) == 48 and len(groups) == 8
            and set(counts.values()) == {6},
            "MINIMAL_48_SOURCE_BIJECTION_HOLD")
    payload = {
        "schema": "storyforge_r60_gold48_reconstructed_inputs_draft_private_v1",
        "status": "RECONSTRUCTED_48_INPUT_DRAFT__OWNER_FREEZE_PENDING",
        "input_contract": "RECONSTRUCTED_EVALUATION_INPUT",
        "historical_actual_sent_verified": False,
        "original_reference_not_read_or_included": True,
        "prompt_owner_freeze": False,
        "anonymized_source_groups": True,
        "cases_PRIVATE": rows,
    }
    require(len(canonical(payload)) <= MAX_FILE_BYTES,
            "STAGED_INPUT_TOO_LARGE_HOLD")
    return payload, sha(draft_raw)


def check_root(root):
    require(root.is_dir() and not root.is_symlink()
            and stat.S_IMODE(root.stat().st_mode) == 0o700,
            "OWNER_PRIVATE_ROOT_HOLD")


def read_private(path, *, maximum=MAX_FILE_BYTES):
    from storyforge_dataset.hf_runtime import InputManager

    require(not path.is_symlink(), "STAGE_SYMLINK_HOLD")
    return InputManager.open_verified(path, max_bytes=maximum).read_bytes()


def verify(stage, run_key):
    require(RUN_RE.fullmatch(run_key) is not None
            and stage.is_dir() and not stage.is_symlink()
            and stat.S_IMODE(stage.stat().st_mode) == 0o700,
            "STAGE_RUN_OR_MODE_HOLD")
    doc = json.loads(read_private(stage / MANIFEST, maximum=32768))
    require(isinstance(doc, dict) and doc.get("schema") == SCHEMA
            and doc.get("run_key") == run_key
            and doc.get("status") == "STAGED_NOT_SUBMITTED"
            and doc.get("candidate_count") == 48
            and doc.get("original_reference_present") is False
            and doc.get("model_revision") ==
            "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0",
            "STAGE_MANIFEST_CONTRACT_HOLD")
    pinned = doc.get("files")
    require(isinstance(pinned, dict)
            and set(pinned) == set(stage_files()) | {INPUT},
            "STAGE_MANIFEST_FILES_HOLD")
    present = set()
    for path in stage.rglob("*"):
        require(not path.is_symlink(), "STAGE_SYMLINK_HOLD")
        if path.is_file():
            present.add(path.relative_to(stage).as_posix())
            require(stat.S_IMODE(path.stat().st_mode) == 0o600,
                    "STAGE_FILE_MODE_HOLD")
        elif path.is_dir():
            require(stat.S_IMODE(path.stat().st_mode) == 0o700,
                    "STAGE_DIRECTORY_MODE_HOLD")
        else:
            raise Hold("STAGE_UNEXPECTED_OBJECT_HOLD")
    require(present == set(pinned) | {MANIFEST},
            "STAGE_FILESET_HOLD")
    for relative, digest in pinned.items():
        require(re.fullmatch(r"[0-9a-f]{64}", digest) is not None
                and sha(read_private(stage / relative)) == digest,
                "STAGE_HASH_BINDING_HOLD")
    staged_raw, _, _ = load_draft(stage / INPUT)
    require(sha(staged_raw) == pinned[INPUT],
            "MINIMAL_INPUT_CONTRACT_HOLD")
    return {
        "schema": "storyforge_r60_gold48_hf_cpu_stage_safe_v1",
        "status": "GOLD48_HF_CPU_STAGE_VERIFIED__NOT_SUBMITTED",
        "run_identity_verified": True,
        "files_verified": len(pinned),
        "case_count": 48,
        "actual_story_ids_staged": False,
        "historical_original_replies_staged": False,
        "job_submitted": False,
        "gpu_started": False,
        "private_values_emitted": False,
    }


def prepare(draft_file, stage, run_key):
    require(RUN_RE.fullmatch(run_key) is not None
            and stage.parent == draft_file.parent.parent
            and stage.name == run_key
            and not stage.exists() and not stage.is_symlink(),
            "PRIVATE_STAGE_PATH_SCOPE_HOLD")
    check_root(stage.parent)
    payload, original_sha = minimally_staged(draft_file)
    stage.mkdir(mode=0o700)
    files = {}
    # Do not remove failed stages: preserve for safe diagnostic and prevent
    # accidental resubmission under the same run key.
    for relative in stage_files():
        src = ROOT / relative
        dst = stage / relative
        dst.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        raw = read_private(src, maximum=8 * 1024 * 1024)
        fd = os.open(dst, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
        files[relative] = sha(raw)
    raw = canonical(payload) + b"\n"
    target = stage / INPUT
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(raw)
    files[INPUT] = sha(raw)
    metadata = {
        "schema": SCHEMA,
        "status": "STAGED_NOT_SUBMITTED",
        "run_key": run_key,
        "candidate_count": 48,
        "source_count": 8,
        "anonymized_group_count": 8,
        "original_reference_present": False,
        "owner_local_original_draft_sha256_PRIVATE": original_sha,
        "input_contract": "RECONSTRUCTED_EVALUATION_INPUT",
        "model": "Qwen/Qwen3.8-27B",
        "model_revision": "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0",
        "files": files,
    }
    raw = canonical(metadata) + b"\n"
    fd = os.open(stage / MANIFEST, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(raw)
    return verify(stage, run_key)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "verify"))
    parser.add_argument("--draft-file", type=Path)
    parser.add_argument("--stage", required=True, type=Path)
    parser.add_argument("--run-key", required=True)
    args = parser.parse_args()
    try:
        result = (prepare(args.draft_file, args.stage, args.run_key)
                  if args.action == "prepare" and args.draft_file is not None
                  else verify(args.stage, args.run_key) if args.action == "verify"
                  else (_ for _ in ()).throw(Hold("STAGE_ARGUMENTS_HOLD")))
    except Exception:  # noqa: BLE001 - no data, paths or exceptions in SAFE
        result = {
            "schema": "storyforge_r60_gold48_hf_cpu_stage_safe_v1",
            "status": "HOLD", "reason_code": "GOLD48_HF_CPU_STAGE_HOLD",
            "job_submitted": False, "gpu_started": False,
            "private_values_emitted": False,
        }
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] != "HOLD" else 42


if __name__ == "__main__":
    raise SystemExit(main())
