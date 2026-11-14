"""Offline reviewer provenance diagnostics for R60 held 336 candidates.

Crosswalk / 1000 evidence is reconstructed by existing shared validator.
Checks review-side evidence shape and frozen model binding only; independence
of providers, hidden context and routes cannot be certified from local files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import r60_real1000_candidate_identity_audit as identity
import r60_real1000_r50_known5_quarantine as quarantine
import r60_real_private_batch as private
import r60_real_quality_batch as batch

SCHEMA = "storyforge_r60_base336_reviewer_provenance_safe_v1"


class Hold(ValueError):
    pass


def inspect(report: dict, manifest: dict, config: dict) -> dict:
    if (manifest.get("schema") != quarantine.SCHEMA
            or manifest.get("status") != "R50_KNOWN5_QUARANTINE__FULL_R50_HOLD"
            or len(manifest.get("remaining_full_r50_hold", [])) != 336
            or len(manifest.get("excluded_known5", [])) != 3
            or report.get("candidate_count") != 339
            or config.get("schema") != batch.SCHEMA
            or config.get("expected_cases") != 1000):
        raise Hold("EVIDENCE_SCOPE_HOLD")
    a, b = config.get("model_a"), config.get("model_b")
    if (not isinstance(a, str) or not a or not isinstance(b, str)
            or not b or a.casefold() == b.casefold()):
        raise Hold("REVIEWER_MODEL_BINDING_HOLD")
    entries = {x["position"]: x for x in report["entries"]}
    counts = Counter()
    positions = set()
    for item in manifest["remaining_full_r50_hold"]:
        pos = item["position"]
        if pos in positions or pos not in entries:
            raise Hold("REVIEWER_POSITION_HOLD")
        positions.add(pos)
        evidence = entries[pos].get("side_evidence")
        if (type(evidence) is not dict or set(evidence) != {"a", "b"}):
            raise Hold("REVIEWER_SIDES_HOLD")
        for side in ("a", "b"):
            row = evidence[side]
            if (type(row) is not dict
                    or row.get("decision") != "PASS"
                    or row.get("source") not in ("V1", "V2", "V3")
                    or not isinstance(row.get("source_receipt_sha256"), str)
                    or len(row["source_receipt_sha256"]) != 64):
                raise Hold("REVIEWER_EVIDENCE_HOLD")
            counts[f"{side}_{row['source']}"] += 1
    if len(positions) != 336:
        raise Hold("REVIEWER_COUNT_HOLD")
    return {
        "schema": SCHEMA,
        "status": "BASE336_REVIEW_EVIDENCE_BOUND__INDEPENDENCE_HOLD",
        "cases_checked": 336,
        "distinct_configured_model_ids": True,
        "v1_pool_config_owner_attestation_present":
            config.get("owner_attested_independent_ai") is True,
        "source_receipts_verified_via_crosswalk_replay": True,
        "side_source_counts": dict(sorted(counts.items())),
        "provider_execution_independence_verified": False,
        "reviewer_independence_verified": False,
        "world_component_isolation_verified": False,
        "r50_complete_exclusion_verified": False,
        "train_admitted": 0, "model_requests": 0,
        "hf_jobs_submitted": 0, "gpu_started": False,
        "private_values_emitted": False, "database_modified": False,
    }


def run(args: argparse.Namespace) -> dict:
    cases, report = identity.verified_cases_report(
        args.old_dir, args.plan_dir, args.v2_dir, args.v3_dir, args.audit_dir)
    raw = private.read_private(
        args.audit_dir / quarantine.crosswalk.FILENAME,
        quarantine.crosswalk.MAX_REPORT)
    manifest = quarantine.construct(
        cases, report, hashlib.sha256(raw).hexdigest())
    saved = json.loads(private.read_private(
        args.quarantine_dir / quarantine.FILENAME,
        quarantine.MAX_PRIVATE_REPORT))
    if manifest != saved:
        raise Hold("QUARANTINE_DRIFT_HOLD")
    config = json.loads(private.read_private(
        args.old_dir / batch.CONFIG_FILE, batch.MAX_CONFIG_BYTES))
    batch.validate_config(args.old_dir)
    return inspect(report, saved, config)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("old", "plan", "v2", "v3", "audit", "quarantine"):
        p.add_argument(f"--{name}-dir", type=Path, required=True)
    args = p.parse_args()
    try:
        out = run(args)
        print(json.dumps(out, sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - no secrets, IDs or private excerpts
        print(json.dumps({
            "schema": SCHEMA, "status": "BASE336_REVIEW_EVIDENCE_HOLD",
            "train_admitted": 0, "model_requests": 0,
            "hf_jobs_submitted": 0, "gpu_started": False,
            "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    sys.exit(main())
