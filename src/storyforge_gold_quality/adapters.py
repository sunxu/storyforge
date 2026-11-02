"""Read-only, bounded adapters for existing R58 SAFE preflight CLIs.

Never forward legacy stdout or stderr. Only known SAFE statuses and integer
counters are exported. Private-input tools are NOT executable via this adapter.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from .manifest import ManifestError

SAFE_CHECKS = {
    "gold87-legacy-index": (
        "experiments/r58_quality/gold87_legacy_index_audit.py",
        "r58_gold87_legacy_index_audit_safe_v1",
        "GOLD87_INDEX_ATTESTATION_ONLY__REVIEW_EVIDENCE_UNBOUND",
        ("frozen_rows_checked", "target_world_identity_present"),
    ),
    "gold108-legacy-binding": (
        "experiments/r58_quality/gold108_review_binding.py",
        "storyforge_r58_gold108_legacy_review_binding_v1",
        "HISTORICAL_DUAL_REVIEW_INDEX_BINDING_ONLY__NO_QUALITY_V1_ADMISSION",
        ("index_count", "review_evidence_count"),
    ),
    "gold195-target-source": (
        "experiments/r58_quality/gold195_target_source.py",
        "r58_gold195_target_source_preflight_v1",
        "SOURCE_TARGET_PREFLIGHT_PASS__QUALITY_ADMISSION_ZERO",
        ("records_checked",),
    ),
}
MAX_STDOUT = 64 * 1024


def available_checks():
    return tuple(SAFE_CHECKS)


def run_safe_check(repo_root: Path, check_id: str) -> dict:
    if check_id not in SAFE_CHECKS:
        raise ManifestError("SAFE_CHECK_NOT_ALLOWLISTED")
    root = repo_root.resolve(strict=True)
    script, schema, status, count_keys = SAFE_CHECKS[check_id]
    path = root / script
    if path.is_symlink() or not path.is_file() or path.resolve(strict=True) != path:
        raise ManifestError("SAFE_CHECK_SCRIPT_UNAVAILABLE")
    # No free-form command or user-supplied script path is accepted.
    try:
        completed = subprocess.run(
            [sys.executable, str(path), "--repo-root", str(root)],
            cwd=root, capture_output=True, text=True, timeout=60,
            check=False, encoding="utf-8", errors="replace",
        )
    except (OSError, subprocess.TimeoutExpired):
        raise ManifestError("SAFE_CHECK_EXECUTION_UNAVAILABLE") from None
    if completed.returncode != 0 or len(completed.stdout) > MAX_STDOUT:
        raise ManifestError("SAFE_CHECK_HOLD")
    try:
        receipt = json.loads(completed.stdout)
    except (TypeError, json.JSONDecodeError):
        raise ManifestError("SAFE_CHECK_BAD_RECEIPT") from None
    if (not isinstance(receipt, dict) or receipt.get("schema") != schema
            or receipt.get("status") != status):
        raise ManifestError("SAFE_CHECK_BAD_STATUS")
    counts = {}
    for key in count_keys:
        value = receipt.get(key)
        if type(value) is not int or value < 0 or value > 10000:
            raise ManifestError("SAFE_CHECK_COUNT_INVALID")
        counts[key] = value
    return {
        "schema": "storyforge_gold_quality_adapter_safe_v1",
        "check": check_id,
        "status": "READ_ONLY_SAFE_CHECK_PASS__NO_ADMISSION",
        "counts": counts,
        "private_values_emitted": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "r50_accessed": False,
    }
