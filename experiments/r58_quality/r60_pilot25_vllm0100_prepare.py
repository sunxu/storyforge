"""Prepare a create-only, Owner-private 25-row A/B HF review pilot; no HF calls.

Read verified 1000-row original HF stage. Copy only 25 blind cases into each
pilot slot. Adapt the pinned vLLM v0.10.0 guided-decoding API names
to a copied reviewer script; do not change frozen source or old stage files.
This does NOT establish GPU image/model compatibility or permit paid Jobs.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import stat
from pathlib import Path

SAFE_SCHEMA = "storyforge_r60_pilot25_vllm0100_prepare_safe_v1"
ROLES = ("A", "B")
ORIG_COUNT = 1000
PILOT_COUNT = 25
SOURCE_SIZE_MAX = 64 * 1024 * 1024
IMAGE = "docker.io/vllm/vllm-openai@sha256:05a31dc4185b042e91f4d2183689ac8a87bd845713d5c3f987563c5899878271"
ALLOWED_BUNDLE = ("runner.py", "token_core.py", "runtime_inputs.py", "runtime_resources.py")


class Hold(ValueError):
    pass


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def checked_file(path: Path, cap: int) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise Hold("SOURCE_FILE_NOT_REGULAR")
    st = path.stat()
    if st.st_nlink != 1 or stat.S_IMODE(st.st_mode) != 0o600:
        raise Hold("SOURCE_FILE_NOT_PRIVATE")
    if not 0 < st.st_size <= cap:
        raise Hold("SOURCE_FILE_SIZE_HOLD")
    return path.read_bytes()


def new_file(path: Path, data: bytes) -> None:
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())


def check_directory(path: Path) -> None:
    if path.is_symlink() or not path.is_dir() or stat.S_IMODE(path.stat().st_mode) != 0o700:
        raise Hold("SOURCE_DIR_NOT_PRIVATE")


def prepare(source: Path, dest: Path) -> dict:
    if source == dest or source.is_relative_to(dest) or dest.is_relative_to(source):
        raise Hold("SOURCE_DESTINATION_COLLISION")
    check_directory(source)
    if dest.exists() or dest.is_symlink():
        raise Hold("DEST_ALREADY_EXISTS")
    check_directory(dest.parent)

    bundles = {}
    inputs = {}
    original_hashes = {}
    pilot_hashes = {}
    for role in ROLES:
        inp = source / f"input_{role}"
        out = source / f"output_{role}"
        check_directory(inp)
        check_directory(out)
        if list(out.glob("review_*.private.json")):
            raise Hold("ORIGINAL_STAGE_ALREADY_REVIEWED")
        original = checked_file(inp / "source.private.jsonl", SOURCE_SIZE_MAX)
        if not original.endswith(b"\n") or len(original.splitlines()) != ORIG_COUNT:
            raise Hold("ORIGINAL_1000_SOURCE_INVALID")
        first = original.splitlines(keepends=True)[:PILOT_COUNT]
        seen = set()
        for line in first:
            try:
                item = json.loads(line)
            except (ValueError, UnicodeError) as exc:
                raise Hold("PILOT_CASE_JSON_INVALID") from exc
            if (not isinstance(item, dict)
                    or set(item) != {"schema", "blind_id", "visible_history", "target_text", "target_semantics", "policy"}
                    or not isinstance(item["blind_id"], str)
                    or not re.fullmatch(r"[a-f0-9]{32}", item["blind_id"])
                    or item["blind_id"] in seen):
                raise Hold("PILOT_INPUT_SCHEMA_INVALID")
            seen.add(item["blind_id"])
        source_files = {name: checked_file(inp / name, 100_000)
                        for name in ALLOWED_BUNDLE}
        runner = source_files["runner.py"].decode("utf-8")
        # The sealed runner can predate the current repository implementation:
        # quote repair might be implemented differently or absent. Change only
        # the verified vLLM API identifiers, not optional control-flow text.
        old_import = "from vllm.sampling_params import StructuredOutputsParams"
        old_type = "StructuredOutputsParams"
        old_kw = "structured_outputs"
        fingerprint = sha(source_files["runner.py"])
        if runner.count(old_import) != 1:
            raise Hold(f"VLLM0100_IMPORT_HOLD__ROLE_{role}__SHA256_{fingerprint}")
        old_type_count = runner.count(old_type)
        old_kw_count = len(re.findall(r"\bstructured_outputs\s*=", runner))
        if old_type_count < 2 or old_kw_count < 1:
            raise Hold(
                f"VLLM0100_API_SHAPE_HOLD__ROLE_{role}"
                f"__TYPE_{old_type_count}__KW_{old_kw_count}"
                f"__SHA256_{fingerprint}"
            )
        runner = runner.replace(old_type, "GuidedDecodingParams")
        runner, changed_kw = re.subn(
            r"\bstructured_outputs(?=\s*=)", "guided_decoding", runner
        )
        if changed_kw != old_kw_count or old_type in runner or re.search(
            r"\bstructured_outputs\s*=", runner
        ):
            raise Hold(f"VLLM0100_RESIDUAL_OLD_API_HOLD__ROLE_{role}")
        try:
            ast.parse(runner)
        except SyntaxError as exc:
            raise Hold(f"VLLM0100_PATCH_SYNTAX_HOLD__ROLE_{role}") from exc
        source_files["runner.py"] = runner.encode("utf-8")
        bundles[role] = source_files
        inputs[role] = b"".join(first)
        original_hashes[role] = sha(original)
        pilot_hashes[role] = sha(inputs[role])

    dest.mkdir(mode=0o700)
    for role in ROLES:
        slot = dest / f"input_{role}"
        slot.mkdir(mode=0o700)
        (dest / f"output_{role}").mkdir(mode=0o700)
        new_file(slot / "source.private.jsonl", inputs[role])
        for name, data in bundles[role].items():
            new_file(slot / name, data)
    return {
        "schema": SAFE_SCHEMA,
        "status": "R60_PILOT25_PRIVATE_STAGED__GPU_NOT_AUTHORIZED",
        "cases_per_role": PILOT_COUNT,
        "source_cases_per_role": ORIG_COUNT,
        "pilot_input_sha256": pilot_hashes,
        "original_input_sha256": original_hashes,
        "model_roles": list(ROLES),
        "image": IMAGE,
        "runner_api": "vllm0100_GuidedDecodingParams_PATCHED_COPY",
        "original_inputs_unchanged": True,
        "hf_jobs_submitted": 0,
        "gpu_started": False,
        "inference_started": False,
        "training_started": False,
        "private_values_emitted": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-stage", type=Path, required=True)
    p.add_argument("--pilot-stage", type=Path, required=True)
    a = p.parse_args()
    try:
        result = prepare(a.source_stage, a.pilot_stage)
        rc = 0
    except (Hold, OSError, UnicodeError, ValueError) as exc:
        result = {
            "schema": SAFE_SCHEMA,
            "status": "R60_PILOT25_PREPARE_HOLD",
            "reason_code": str(exc) if isinstance(exc, Hold) else "PRIVATE_SOURCE_OR_IO_HOLD",
            "hf_jobs_submitted": 0,
            "gpu_started": False,
            "private_values_emitted": False,
        }
        rc = 42
    print(json.dumps(result, sort_keys=True))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
