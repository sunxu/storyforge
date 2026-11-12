"""Read-only HF Bucket run-prefix guard; fail closed on API failure."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

BUCKET = "adradar/storyforge-training"
ROOT = "preflight/r60/common2/cpu2/runs"
PATTERN = re.compile(r"r60-common2-cpu2-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{12}\Z")


def expected(stage: Path) -> set[str]:
    manifest = stage / "SHA256SUMS.txt"
    if not manifest.is_file():
        raise ValueError("LOCAL_MANIFEST_MISSING")
    result = {"SHA256SUMS.txt"}
    for line in manifest.read_text().splitlines():
        hash_hex, separator, path = line.partition("  ")
        if (not separator or len(hash_hex) != 64 or
                any(c not in "0123456789abcdef" for c in hash_hex)
                or not path.startswith(("code/", "private_stage/"))
                or ".." in Path(path).parts or path in result):
            raise ValueError("LOCAL_MANIFEST_UNSAFE")
        result.add(path)
    return result


def check(mode: str, run_key: str, stage: Path, api) -> None:
    if not PATTERN.fullmatch(run_key):
        raise ValueError("RUN_KEY_HOLD")
    prefix = f"{ROOT}/{run_key}/"
    paths: set[str] = set()
    for entry in api.list_bucket_tree(BUCKET, prefix=prefix, recursive=True):
        path = getattr(entry, "path", None)
        if not isinstance(path, str) or not path.startswith(prefix):
            raise ValueError("REMOTE_PREFIX_ENTRY_HOLD")
        if getattr(entry, "type", "") == "directory":
            continue
        relative = path[len(prefix):]
        if not relative or relative in paths:
            raise ValueError("REMOTE_DUPLICATE_ENTRY_HOLD")
        paths.add(relative)
    if mode == "empty":
        if paths:
            raise ValueError("REMOTE_RUN_ALREADY_EXISTS")
    elif mode == "ready":
        if paths != expected(stage):
            raise ValueError("REMOTE_RUN_FILESET_HOLD")
    else:
        raise ValueError("MODE_HOLD")


def classify_failure(exc: Exception) -> str:
    """Only allowlisted failure categories; never print remote/private details."""
    if isinstance(exc, ModuleNotFoundError):
        return "SDK_MODULE_MISSING"
    if isinstance(exc, AttributeError):
        return "SDK_API_UNAVAILABLE"
    if isinstance(exc, TypeError):
        return "SDK_API_INCOMPATIBLE"
    if isinstance(exc, ValueError):
        valid = {
            "RUN_KEY_HOLD", "REMOTE_PREFIX_ENTRY_HOLD",
            "REMOTE_DUPLICATE_ENTRY_HOLD", "REMOTE_RUN_ALREADY_EXISTS",
            "REMOTE_RUN_FILESET_HOLD", "MODE_HOLD",
            "LOCAL_MANIFEST_MISSING", "LOCAL_MANIFEST_UNSAFE",
        }
        return str(exc) if str(exc) in valid else "INPUT_VALIDATION_HOLD"
    status = getattr(getattr(exc, "response", None), "status_code", None)
    if status in (401, 403):
        return "REMOTE_AUTHORIZATION_HOLD"
    if status == 404:
        return "REMOTE_BUCKET_OR_PATH_NOT_FOUND_HOLD"
    if isinstance(exc, (ConnectionError, TimeoutError, OSError)):
        return "REMOTE_CONNECTION_HOLD"
    return "REMOTE_SDK_OR_SERVICE_HOLD"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=("empty", "ready"))
    p.add_argument("run_key")
    p.add_argument("--stage", type=Path, required=True)
    a = p.parse_args()
    try:
        from huggingface_hub import HfApi
        check(a.mode, a.run_key, a.stage, HfApi())
        print("R60_COMMON2_HF_CPU2_REMOTE_" + a.mode.upper() + "_PASS")
        return 0
    except Exception as exc:  # noqa: BLE001 - fail closed; only expose allowlisted reason
        print("R60_COMMON2_HF_CPU2_REMOTE_PREFIX_HOLD", file=sys.stderr)
        print("R60_COMMON2_REASON_CODE=" + classify_failure(exc), file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
