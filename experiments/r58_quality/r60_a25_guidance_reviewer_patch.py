"""Create-only frozen A25 reviewer copy selecting vLLM Guidance backend.

Scoped response to actual Qwen A25 XGrammar failure at request 6. Does not
change prompts, input, schema, rubric, generation temperature or checkpoints.
The only transformation is GuidedDecodingParams(json=response_schema())
to GuidedDecodingParams(json=response_schema(), backend="guidance").

Run on Owner Mac, CPU-only, producing a new isolated runner.py. Keep original
frozen runner.py intact. Resume checks existing checkpoints before inference.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path

SCHEMA = "storyforge_r60_a25_guidance_reviewer_patch_safe_v1"
NEEDLE = "GuidedDecodingParams(json=response_schema())"
REPLACEMENT = 'GuidedDecodingParams(json=response_schema(), backend="guidance")'


class Hold(ValueError):
    pass


def patch(source: Path, dest: Path) -> dict:
    if (source.is_symlink() or not source.is_file() or
            dest.exists() or dest.is_symlink()
            or not dest.parent.is_dir() or dest.parent.is_symlink()
            or dest.parent.resolve() == source.parent.resolve()):
        raise Hold("PATCH_PATH_HOLD")
    raw = source.read_bytes()
    if len(raw) > 200_000:
        raise Hold("PATCH_SOURCE_SIZE_HOLD")
    original_sha = hashlib.sha256(raw).hexdigest()
    try:
        script = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise Hold("PATCH_UTF8_HOLD") from exc
    if (script.count(NEEDLE) != 1
            or script.count("from vllm.sampling_params import GuidedDecodingParams") != 1
            or script.count("guided_decoding=GuidedDecodingParams") != 0
            or 'backend="guidance"' in script):
        raise Hold("PATCH_FROZEN_RUNNER_SHAPE_HOLD")
    ast.parse(script)
    changed = script.replace(NEEDLE, REPLACEMENT)
    ast.parse(changed)
    if changed.count(REPLACEMENT) != 1:
        raise Hold("PATCH_RESULT_SHAPE_HOLD")
    fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as out:
        out.write(changed.encode())
        out.flush()
        os.fsync(out.fileno())
    return {
        "schema": SCHEMA, "status": "PATCH_GUIDANCE_ONLY_READY",
        "source_sha256": original_sha,
        "patched_sha256": hashlib.sha256(changed.encode()).hexdigest(),
        "changed_occurrences": 1, "gpu_started": False,
        "training_authorized": False, "private_values_emitted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--dest", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = patch(args.source, args.dest)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - never expose private paths
        print(json.dumps({"schema": SCHEMA, "status": "PATCH_HOLD",
                          "reason_code": str(exc) if isinstance(exc, Hold)
                          else "PATCH_RUNTIME_REDACTED",
                          "private_values_emitted": False}, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
