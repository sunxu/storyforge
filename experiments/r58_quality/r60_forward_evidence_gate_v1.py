"""R60 forward-only quality intake gates: seal evidence BEFORE model calls.

This module is intentionally NOT wired into the frozen V1/V2/V3 runners.
A future V2 dispatcher must call require_pre_review() before either request,
and require_post_review() before publishing any candidate. Synthetic tests only.
No claims that historical 336 were independently reviewed.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone

SCHEMA = "storyforge_r60_forward_evidence_gate_v1"
DIGEST = re.compile(r"[a-f0-9]{64}\Z")
ID = re.compile(r"[A-Za-z0-9_.:-]{8,128}\Z")


class Hold(ValueError):
    pass


def sha(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def _digest(value: object) -> bool:
    return type(value) is str and DIGEST.fullmatch(value) is not None


def _utc(value: object) -> datetime:
    if type(value) is not str or not value.endswith("Z"):
        raise Hold("TIMESTAMP_HOLD")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise Hold("TIMESTAMP_HOLD") from exc
    if parsed.tzinfo != timezone.utc:
        raise Hold("TIMESTAMP_HOLD")
    return parsed


def require_pre_review(source: dict, protection: dict, world: dict) -> dict:
    """Fail closed unless frozen source, protected set, and world split proved.

    External semantic/R50 evidence is checked for bindings, NOT independently
    re-adjudicated here. A trusted human/independent review must supply these.
    """
    if (type(source) is not dict or source.get("schema") != SCHEMA
            or source.get("source_snapshot_frozen") is not True
            or source.get("historical_cutoff_verified") is not True
            or not all(_digest(source.get(k)) for k in (
                "source_sha256", "case_sha256", "source_revision_sha256",
                "history_sha256", "target_sha256"))
            or not isinstance(source.get("story_key_private"), str)
            or not source["story_key_private"]):
        raise Hold("FROZEN_SOURCE_HOLD")
    if (type(protection) is not dict
            or protection.get("manifest_frozen") is not True
            or protection.get("covers_all_protected_sets") is not True
            or protection.get("exact_identity_disjoint") is not True
            or protection.get("semantic_overlap_cleared") is not True
            or not _digest(protection.get("manifest_sha256"))
            or protection.get("case_sha256") != source["case_sha256"]):
        raise Hold("EVALUATION_PROTECTION_HOLD")
    if (type(world) is not dict
            or world.get("source_bound_roles_and_world") is not True
            or world.get("semantic_components_adjudicated") is not True
            or world.get("all_uncertain_links_quarantined") is not True
            or world.get("train_validation_component_disjoint") is not True
            or world.get("case_sha256") != source["case_sha256"]
            or not _digest(world.get("component_manifest_sha256"))
            or world.get("split") not in ("train", "validation")
            or world.get("component_key_private") in (None, "")):
        raise Hold("WORLD_COMPONENT_HOLD")
    seal = {
        "schema": SCHEMA, "case_sha256": source["case_sha256"],
        "source_sha256": source["source_sha256"],
        "source_revision_sha256": source["source_revision_sha256"],
        "history_sha256": source["history_sha256"],
        "target_sha256": source["target_sha256"],
        "protected_manifest_sha256": protection["manifest_sha256"],
        "component_manifest_sha256": world["component_manifest_sha256"],
        "split": world["split"],
        "provenance_kind": "PRE_REVIEW_SOURCE_AND_EVAL_FROZEN",
    }
    return {**seal, "pre_review_seal_sha256": sha(seal)}


def require_post_review(seal: dict, executions: list[dict]) -> dict:
    """Reject missing provider-backed evidence; NO automatic train admission.

    Request IDs must originate at transport/provider; random local IDs,
    timestamps and hashes by themselves are insufficient as proof.
    """
    if (type(seal) is not dict or seal.get("schema") != SCHEMA
            or not _digest(seal.get("pre_review_seal_sha256"))
            or sha({k: v for k, v in seal.items()
                    if k != "pre_review_seal_sha256"})
            != seal["pre_review_seal_sha256"]):
        raise Hold("PRE_REVIEW_SEAL_HOLD")
    if type(executions) is not list or len(executions) != 2:
        raise Hold("TWO_EXECUTIONS_REQUIRED_HOLD")
    ids = set()
    model_ids = set()
    seen = set()
    for row in executions:
        if type(row) is not dict or row.get("side") not in ("a", "b"):
            raise Hold("EXECUTION_SIDE_HOLD")
        seen.add(row["side"])
        if (row.get("case_sha256") != seal["case_sha256"]
                or row.get("pre_review_seal_sha256")
                != seal["pre_review_seal_sha256"]
                or row.get("input_sha256") != seal["history_sha256"]
                or not _digest(row.get("review_prompt_sha256"))
                or not _digest(row.get("response_sha256"))):
            raise Hold("EXECUTION_BINDING_HOLD")
        if (not isinstance(row.get("provider"), str) or not row["provider"]
                or not isinstance(row.get("model_id"), str)
                or not row["model_id"]):
            raise Hold("EXECUTION_ROUTE_HOLD")
        if (type(row.get("provider_request_id")) is not str or
                ID.fullmatch(row["provider_request_id"]) is None
                or row.get("provider_request_id_origin") != "PROVIDER_RESPONSE"
                or row.get("provider_evidence_authenticated") is not True):
            raise Hold("AUTHENTICATED_PROVIDER_EVIDENCE_HOLD")
        if (row.get("http_status") != 200
                or row.get("review_decision") != "PASS"
                or row.get("review_criteria_frozen") is not True
                or row.get("other_reviewer_output_in_request") is not False
                or row.get("isolated_context_verified") is not True):
            raise Hold("REVIEW_EXECUTION_HOLD")
        start = _utc(row.get("started_at_utc"))
        end = _utc(row.get("finished_at_utc"))
        if end < start:
            raise Hold("EXECUTION_TIME_HOLD")
        ids.add((row["provider"], row["provider_request_id"]))
        model_ids.add((row["provider"], row["model_id"]))
    if len(ids) != 2 or len(model_ids) != 2 or seen != {"a", "b"}:
        raise Hold("EXECUTION_INDEPENDENCE_HOLD")
    return {
        "schema": SCHEMA,
        "status": "FORWARD_EVIDENCE_BOUND__TRAIN_HOLD",
        "case_sha256": seal["case_sha256"],
        "pre_review_seal_sha256": seal["pre_review_seal_sha256"],
        "authenticated_two_side_execution_records": 2,
        "reviewer_execution_independence_claim_supported": True,
        "external_evidence_authentication_required": True,
        "train_admitted": 0, "gpu_started": False,
        "model_requests_performed_by_gate": 0,
    }
