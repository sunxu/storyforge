"""R58: verify an EXISTING priority HF provider-metadata receipt, read-only.

No HF/DB calls, no historical log reads, no new receipt, no raw Job IDs,
private SHA values, sensitive command text, or source paths on stdout.
This checks a previously saved receipt's internal provenance, NOT training.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from r58_g1_scope_reconcile import Hold, read_private

SCHEMA = "r58_existing_priority_metadata_crosscheck_safe_v1"
PRIORITY_SCHEMA = "r58_round1_g1_gpu_signal_priority_case_private_v1"
RECEIPT_SCHEMA = "r58_round1_g1_hf_priority_job_metadata_private_v1"
PRIORITY_FIELDS = frozenset({
    "schema", "status", "namespace", "hf_job_id_PRIVATE", "stage",
    "indicator_classes", "prior_gpu_log_sha256_PRIVATE",
    "update_proof_status", "training_input_sha256_status",
    "train_validation_usage_status", "r50_content_accessed_this_step",
    "g1_clearance", "expansion_allowed",
})
RECEIPT_FIELDS = frozenset({
    "schema", "status", "namespace", "hf_job_id_PRIVATE",
    "prior_gpu_log_sha256_PRIVATE", "provider_started_at_present",
    "provider_finished_at_present", "command_intent_class",
    "no_optimizer_update_proof", "primary_inputs_not_verified",
    "g1_clearance", "expansion_allowed",
})
COMMAND_CLASSES = frozenset({
    "NOT_ACCESSED_NO_OWNER_OPT_IN", "POTENTIAL_TRAINING_COMMAND_INTENT",
    "NO_TRAINING_COMMAND_MARKER__NOT_EXCLUDED", "COMMAND_UNAVAILABLE_PENDING",
    "UNINSPECTABLE_PENDING", "BOUNDED_COMMAND_PENDING",
})
ID = re.compile(r"[a-f0-9]{24}\Z")
SHA = re.compile(r"[a-f0-9]{64}\Z")


def verify(priority: dict, receipt: dict) -> dict:
    """Fail closed on changed identity/lineage while emitting SAFE booleans."""
    if not isinstance(priority, dict) or set(priority) != PRIORITY_FIELDS:
        raise Hold("priority schema fields mismatch")
    if not isinstance(receipt, dict) or set(receipt) != RECEIPT_FIELDS:
        raise Hold("provider metadata schema fields mismatch")
    job_id = priority["hf_job_id_PRIVATE"]
    log_sha = priority["prior_gpu_log_sha256_PRIVATE"]
    if (priority["schema"] != PRIORITY_SCHEMA
            or priority["status"] != "ONE_POTENTIAL_LOG_INDICATOR__PROOF_NOT_ESTABLISHED"
            or priority["namespace"] != "adradar"
            or not isinstance(job_id, str) or not ID.fullmatch(job_id)
            or priority["stage"] != "CANCELED"
            or priority["indicator_classes"] != ["TRAINING_LOSS_GRAD_TELEMETRY"]
            or not isinstance(log_sha, str) or not SHA.fullmatch(log_sha)
            or priority["update_proof_status"] != "PENDING_PRIMARY_RUN_ARTIFACT"
            or priority["training_input_sha256_status"] != "NOT_VERIFIED"
            or priority["train_validation_usage_status"] != "NOT_VERIFIED"
            or priority["r50_content_accessed_this_step"] is not False
            or priority["g1_clearance"] != "HOLD"
            or priority["expansion_allowed"] is not False):
        raise Hold("priority source is not an accepted pending case")
    if (receipt["schema"] != RECEIPT_SCHEMA
            or receipt["status"] != "CANCELED_GPU_PROVIDER_METADATA_ONLY__NO_UPDATE_PROOF"
            or receipt["namespace"] != "adradar"
            or receipt["hf_job_id_PRIVATE"] != job_id
            or receipt["prior_gpu_log_sha256_PRIVATE"] != log_sha
            or type(receipt["provider_started_at_present"]) is not bool
            or type(receipt["provider_finished_at_present"]) is not bool
            or receipt["command_intent_class"] not in COMMAND_CLASSES
            or receipt["no_optimizer_update_proof"] is not True
            or receipt["primary_inputs_not_verified"] is not True
            or receipt["g1_clearance"] != "HOLD"
            or receipt["expansion_allowed"] is not False):
        raise Hold("provider metadata does not match frozen priority")
    return {
        "schema": SCHEMA,
        "status": "EXISTING_PRIORITY_METADATA_CROSSLINK_VERIFIED__PARAMETER_AND_INPUT_HOLD",
        "existing_private_receipt_reused": True,
        "hf_api_called": False,
        "job_id_and_log_sha_match_private_priority": True,
        "provider_stage": "CANCELED",
        "provider_started_at_present": receipt["provider_started_at_present"],
        "provider_finished_at_present": receipt["provider_finished_at_present"],
        "command_intent_class": receipt["command_intent_class"],
        "provider_metadata_evidence_present": True,
        "actual_optimizer_update_proven": False,
        "confirmed_no_optimizer_update": False,
        "actual_training_input_sha256_verified": False,
        "historical_training_universe_complete": False,
        "r50_content_read": False,
        "private_job_ids_or_hashes_exported": False,
        "private_metadata_written": False,
        "g1_clearance": "HOLD",
        "g2_clearance": "HOLD",
        "train_admitted": 0,
        "validation_admitted": 0,
        "teacher_admitted": 0,
        "expansion_allowed": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-priority-ledger", required=True, type=Path)
    parser.add_argument("--existing-private-metadata", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        root = Path.home() / ".storyforge-r58-private"
        if args.private_priority_ledger == args.existing_private_metadata:
            raise Hold("metadata receipt and priority source are the same path")
        source = read_private(args.private_priority_ledger, root)
        receipt = read_private(args.existing_private_metadata, root)
        print(json.dumps(verify(source, receipt), ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except (Hold, OSError, ValueError, TypeError, UnicodeError, KeyError):
        print("R58_G1_EXISTING_PRIORITY: HOLD (private receipts unavailable or inconsistent)",
              file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
