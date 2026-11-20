"""Gold48 isolated CPU-only two-Job test of the EXISTING OutputManager.

Do not point this at the real Owner authorization ledger or output directory.
Stage this script AND the exact repository hf_runtime/outputs.py read-only.
The first HF Job writes a synthetic create-only marker. A different HF Job
verifies the unchanged marker. No Owner receipts, adapter bytes, models or GPU.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import stat
import sys
from pathlib import Path

# Independent Git blob pin from the already reviewed hf_runtime/outputs.py.
OUTPUTS_GIT_BLOB_SHA1 = "69838b603b43663eaa12b1b1947ce14abad524bc"
SCHEMA = "storyforge_gold48_ledger_atomic_cpu_probe_safe_v1"
MARKER_SCHEMA = "storyforge_gold48_ledger_atomic_synthetic_marker_v1"
PROBE_ID = re.compile(r"gold48-[a-z0-9-]{8,48}\\Z")
MAX_SOURCE_BYTES = 20_000


class ProbeHold(ValueError):
    pass


def _check(value: bool, reason: str) -> None:
    if not value:
        raise ProbeHold(reason)


def _existing_output_manager(source: Path):
    """Load the unchanged reviewed standard-library publisher, no fork."""
    try:
        st = source.lstat()
        _check(stat.S_ISREG(st.st_mode), "PINNED_OUTPUT_MODULE_NOT_FILE_HOLD")
        raw = source.read_bytes()
        _check(len(raw) <= MAX_SOURCE_BYTES,
               "PINNED_OUTPUT_MODULE_SIZE_HOLD")
        git_sha = hashlib.sha1(
            b"blob " + str(len(raw)).encode("ascii") + b"\\0" + raw,
        ).hexdigest()
        _check(git_sha == OUTPUTS_GIT_BLOB_SHA1,
               "PINNED_OUTPUT_MODULE_SHA_HOLD")
        spec = importlib.util.spec_from_file_location(
            "gold48_probe_existing_outputmanager", str(source)
        )
        _check(spec is not None and spec.loader is not None,
               "PINNED_OUTPUT_MODULE_LOAD_HOLD")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module.OutputManager
    except (OSError, UnicodeError, ImportError) as exc:
        raise ProbeHold("PINNED_OUTPUT_MODULE_READ_HOLD") from exc


def _mount_root(root: Path) -> None:
    """Must be the exact RW mount, not a container-local lookalike directory."""
    try:
        st = root.lstat()
        _check(stat.S_ISDIR(st.st_mode)
               and stat.S_IMODE(st.st_mode) == 0o700,
               "MOUNT_DIRECTORY_MODE_0700_HOLD")
        _check(root.is_mount(), "DIRECT_PERSISTENT_MOUNT_REQUIRED_HOLD")
        rows = Path("/proc/self/mountinfo").read_text(encoding="utf-8").splitlines()
        mount_options = []
        for line in rows:
            before, sep, _ = line.partition(" - ")
            if not sep:
                continue
            parts = before.split()
            if len(parts) >= 6 and parts[4] == str(root):
                mount_options.append(parts[5].split(","))
        _check(len(mount_options) == 1 and "rw" in mount_options[0],
               "MOUNT_RW_OPTION_REQUIRED_HOLD")
    except (OSError, UnicodeError) as exc:
        raise ProbeHold("MOUNT_INSPECT_HOLD") from exc


def _payload() -> dict[str, object]:
    return {
        "schema": MARKER_SCHEMA,
        "owner_authorization": False,
        "model_calls": 0,
        "synthetic_marker": "NO_PRIVATE_DATA",
    }


def _read_and_check_marker(path: Path) -> str:
    try:
        st = path.lstat()
        _check(stat.S_ISREG(st.st_mode)
               and stat.S_IMODE(st.st_mode) == 0o600
               and 1 <= st.st_size <= 1024,
               "PERSISTED_MARKER_MODE_OR_SIZE_HOLD")
        raw = path.read_bytes()
        actual = json.loads(raw)
        _check(actual == _payload()
               and set(actual) == set(_payload()),
               "PERSISTED_MARKER_CONTENT_HOLD")
        # Existing OutputManager's documented canonical JSON publication.
        expected = (
            json.dumps(_payload(), ensure_ascii=False, sort_keys=True,
                       separators=(",", ":")) + "\\n"
        ).encode("utf-8")
        _check(raw == expected, "PERSISTED_MARKER_BYTES_HOLD")
        return hashlib.sha256(raw).hexdigest()
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        if isinstance(exc, ProbeHold):
            raise
        raise ProbeHold("PERSISTED_MARKER_READ_HOLD") from exc


def _reject_overwrite(publisher, path: Path) -> None:
    try:
        publisher.write_safe(
            path, {"schema": "MUST_NEVER_REPLACE_EXISTING_MARKER"}, mode=0o600
        )
    except ValueError as exc:
        _check(str(exc) == "OUTPUT_ALREADY_EXISTS",
               "ATOMIC_NO_REPLACE_UNSUPPORTED_HOLD")
    else:
        raise ProbeHold("ATOMIC_NO_REPLACE_UNSUPPORTED_HOLD")


def run(*, phase: str, root: Path, source: Path,
        probe_id: str) -> dict[str, object]:
    """No external network, no remote submission and no private inputs."""
    _check(bool(PROBE_ID.fullmatch(probe_id)), "PROBE_ID_FORMAT_HOLD")
    _check(phase in {"write", "verify"}, "PROBE_PHASE_HOLD")
    _mount_root(root)
    publisher = _existing_output_manager(source)
    marker = root / ("." + probe_id + ".private.json")
    if phase == "write":
        _check(not marker.exists() and not marker.is_symlink(),
               "SYNTHETIC_PROBE_ALREADY_EXISTS_HOLD")
        try:
            receipt = publisher.write_safe(marker, _payload(), mode=0o600)
        except (ValueError, OSError) as exc:
            raise ProbeHold("ATOMIC_PUBLISH_UNSUPPORTED_HOLD") from exc
        actual_sha = _read_and_check_marker(marker)
        _check(receipt.sha256 == actual_sha and receipt.mode == 0o600,
               "OUTPUTMANAGER_RECEIPT_MISMATCH_HOLD")
        _reject_overwrite(publisher, marker)
        status = "ATOMIC_CREATE_ONLY_CPU_PASS__SECOND_JOB_PENDING"
    else:
        _check(marker.exists() and not marker.is_symlink(),
               "CROSS_JOB_MARKER_MISSING_HOLD")
        actual_sha = _read_and_check_marker(marker)
        _reject_overwrite(publisher, marker)
        status = "ATOMIC_CREATE_ONLY_AND_CROSS_JOB_PERSISTENCE_CPU_PASS"
    return {
        "schema": SCHEMA,
        "status": status,
        "phase": phase,
        "direct_rw_mount_present": True,
        "root_mode_0700": True,
        "marker_mode_0600": True,
        "marker_sha256": actual_sha,
        "existing_outputmanager_git_blob_verified": True,
        "atomic_create_only_verified": True,
        "cross_job_persistence_verified": phase == "verify",
        "gpu_started": False,
        "model_calls": 0,
        "weights_read": False,
        "training_started": False,
        "private_values_emitted": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", required=True, choices=("write", "verify"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--probe-id", required=True)
    args = parser.parse_args(argv)
    try:
        report = run(
            phase=args.phase, root=args.root,
            source=args.source, probe_id=args.probe_id,
        )
        exit_code = 0
    except (ProbeHold, OSError, TypeError, ValueError) as exc:
        report = {
            "schema": SCHEMA,
            "status": "HOLD",
            "reason_code": str(exc) if isinstance(exc, ProbeHold)
                           else "UNEXPECTED_CPU_PROBE_HOLD",
            "gpu_started": False,
            "model_calls": 0,
            "weights_read": False,
            "training_started": False,
            "private_values_emitted": False,
        }
        exit_code = 2
    print(json.dumps(report, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
