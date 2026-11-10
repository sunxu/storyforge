"""CPU-only strict pairing check for private P4 formal evaluation inputs.

Never contacts Hugging Face, loads a model, or prints private case identifiers
or message contents. This is a *structural* check, not proof of label isolation,
source rights, token budget, quality, or execution authorization.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROLES = ("A", "B", "challenger")
TRACK_COUNTS = {"S": 30, "W-pilot": 6, "W": 12}
SAMPLE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$")
MESSAGE_ROLES = frozenset({"system", "developer", "user", "assistant"})
DISALLOWED_KEYS = frozenset({
    "owner_label", "owner_labels", "owner_verdict", "owner_resolution",
    "reference_label", "reference_labels", "reference_answer",
    "gold_answer", "ground_truth", "blind_id_map",
    "expected_output", "target_response", "target_answer",
})
MAX_FILE_BYTES = 64 * 1024 * 1024


class FormalPairingError(ValueError):
    """Reject malformed/unpaired private formal evaluation input files."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load(path: Path, expected_count: int) -> tuple[str, dict[str, str], str]:
    if path.is_symlink() or not path.is_file():
        raise FormalPairingError("INPUT_NOT_REGULAR_FILE")
    if path.stat().st_size > MAX_FILE_BYTES:
        raise FormalPairingError("INPUT_FILE_TOO_LARGE")
    raw = path.read_bytes()
    if not raw or not raw.endswith(b"\n"):
        raise FormalPairingError("INPUT_JSONL_ENDING_INVALID")
    lines = raw.splitlines()
    if len(lines) != expected_count:
        raise FormalPairingError("INPUT_RECORD_COUNT_MISMATCH")
    records: dict[str, str] = {}
    for line in lines:
        try:
            obj = json.loads(line)
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise FormalPairingError("INPUT_JSONL_INVALID") from exc
        if not isinstance(obj, dict) or set(obj) != {"sample_id", "messages"}:
            raise FormalPairingError("INPUT_RECORD_SCHEMA_INVALID")
        case_id = obj["sample_id"]
        if not isinstance(case_id, str) or not SAMPLE_ID.fullmatch(case_id):
            raise FormalPairingError("INPUT_SAMPLE_ID_INVALID")
        if case_id in records:
            raise FormalPairingError("INPUT_DUPLICATE_SAMPLE_ID")
        messages = obj["messages"]
        if not isinstance(messages, list) or not 1 <= len(messages) <= 64:
            raise FormalPairingError("INPUT_MESSAGES_INVALID")
        for message in messages:
            if (
                not isinstance(message, dict)
                or set(message) != {"role", "content"}
                or not isinstance(message["role"], str)
                or message["role"] not in MESSAGE_ROLES
                or not isinstance(message["content"], str)
                or not message["content"].strip()
            ):
                raise FormalPairingError("INPUT_MESSAGE_SCHEMA_INVALID")
        if messages[-1]["role"] != "user":
            raise FormalPairingError("INPUT_MUST_END_WITH_USER")
        if any(key in DISALLOWED_KEYS for key in obj):
            raise FormalPairingError("REFERENCE_KEY_FORBIDDEN")
        records[case_id] = _sha(_canonical(messages))
    paired_set_digest = _sha(_canonical(sorted(records)))
    return _sha(raw), records, paired_set_digest


def assess_pairing(*, track: str, paths: dict[str, Path]) -> dict[str, Any]:
    """Return only hashed SAFE metrics; file reading is local and CPU-only."""
    if track not in TRACK_COUNTS:
        raise FormalPairingError("TRACK_INVALID")
    if set(paths) != set(ROLES):
        raise FormalPairingError("MODEL_SET_INVALID")
    count = TRACK_COUNTS[track]
    fingerprints: dict[str, str] = {}
    by_role: dict[str, dict[str, str]] = {}
    case_sha: str | None = None
    for role in ROLES:
        sha, cases, role_case_sha = _load(paths[role], count)
        fingerprints[role] = sha
        by_role[role] = cases
        if case_sha is None:
            case_sha = role_case_sha
        elif role_case_sha != case_sha:
            raise FormalPairingError("CASE_SET_MISMATCH")
    reference = by_role["A"]
    for role in ROLES[1:]:
        for case_id, message_sha in reference.items():
            if by_role[role][case_id] != message_sha:
                raise FormalPairingError("PAIRED_MESSAGES_DIFFER")
    return {
        "schema": "storyforge_r60_p4_formal_pairing_safe_v1",
        "status": "FORMAL_PAIRING_STRUCTURE_PASS__OTHER_GATES_PENDING",
        "track": track,
        "record_count_per_role": count,
        "unique_case_count": len(reference),
        "case_id_set_sha256": case_sha,
        "input_sha256_by_role": fingerprints,
        "messages_exactly_paired": True,
        "reference_label_absence_verified": False,
        "story_scope_verified": False,
        "input_token_budget_verified": False,
        "formal_gpu_authorized": False,
        "hf_jobs_submitted": 0,
        "gpu_started": False,
        "inference_started": False,
        "training_started": False,
        "private_values_emitted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--track", required=True, choices=tuple(TRACK_COUNTS))
    for role in ROLES:
        parser.add_argument(f"--{role}", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = assess_pairing(
            track=args.track,
            paths={role: getattr(args, role) for role in ROLES},
        )
    except (FormalPairingError, OSError, TypeError, ValueError) as exc:
        reason = str(exc) if isinstance(exc, FormalPairingError) else "INPUT_READ_FAILED"
        result = {
            "schema": "storyforge_r60_p4_formal_pairing_safe_v1",
            "status": "FORMAL_PAIRING_HOLD",
            "reason_code": reason,
            "hf_jobs_submitted": 0,
            "gpu_started": False,
            "inference_started": False,
            "training_started": False,
            "private_values_emitted": False,
        }
        print(json.dumps(result, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
