"""R60 forward-only Reviewer V2 *synthetic transport* execution ledger.

Execution sequence is deliberately irreversible:
pre-review gate -> 0600 seal -> each request -> 0600 side event.
A missing event, unknown transport identity, or any failure => HOLD, no retry.
This is a reference dispatcher, NOT connected to live Provider/network routes.
Provider IDs seen in a mock/HTTP envelope are not authenticated independently.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable

import r60_forward_evidence_gate_v1 as gate
import r60_real_ai_dual_review as ai
import r60_real_private_batch as private
import r60_reviewer_transport as protocol

SCHEMA = "storyforge_r60_forward_reviewer_v2_ledger_private_v1"
SAFE = "storyforge_r60_forward_reviewer_v2_ledger_safe_v1"


class Hold(ValueError):
    pass


def _new_file(path: Path, payload: dict) -> None:
    raw = (json.dumps(payload, sort_keys=True, ensure_ascii=False) + "\n").encode()
    if len(raw) > 80_000:
        raise Hold("LEDGER_SIZE_HOLD")
    private.write_new(path, raw)


def _validate_specs(specs: list[dict]) -> None:
    if (type(specs) is not list or len(specs) != 2
            or [row.get("side") for row in specs] != ["a", "b"]):
        raise Hold("TWO_REVIEWER_ROUTES_HOLD")
    routes = set()
    for row in specs:
        if (not isinstance(row.get("provider"), str) or not row["provider"]
                or not isinstance(row.get("model_id"), str) or not row["model_id"]
                or not isinstance(row.get("profile"), str)
                or not isinstance(row.get("json_mode"), bool)):
            raise Hold("REVIEW_ROUTE_HOLD")
        try:
            protocol.require_profile(row["profile"])
        except ValueError as exc:
            raise Hold("REVIEW_ROUTE_HOLD") from exc
        routes.add((row["provider"], row["model_id"]))
    if len(routes) != 2:
        raise Hold("TWO_DISTINCT_ROUTES_HOLD")


def execute_synthetic(
    *, output_dir: Path, source: dict, protection: dict, world: dict,
    case: dict, specs: list[dict],
    transport: Callable[[str, dict], dict],
) -> dict:
    """Synthetic only. Callable must not send network requests.

    Stub returns parsed review, envelope metadata and observed timestamp.
    A completed transport observation without independently authenticated
    provider traces is retained for later correlation but NEVER PASS evidence.
    """
    _validate_specs(specs)
    seal = gate.require_pre_review(source, protection, world)
    if (case.get("history_messages_sha256") != seal["history_sha256"]
            or case.get("assistant_target_sha256") != seal["target_sha256"]):
        raise Hold("CASE_SOURCE_BINDING_HOLD")
    prompt = ai.prompt_for_case(case)
    if (output_dir.exists() or output_dir.is_symlink()
            or output_dir.parent != private.BASE):
        raise Hold("LEDGER_CREATE_ONLY_HOLD")
    private.private_dir(output_dir, create=True)
    _new_file(output_dir / "PRE_REVIEW_SEAL_PRIVATE.json", seal)

    seen_sides = 0
    for spec in specs:
        side = spec["side"]
        # Input contains source case only, NEVER earlier reviewer output.
        body = protocol.build_body(
            model=spec["model_id"], prompt=prompt,
            instructions=ai.REVIEW_INSTRUCTIONS_V3_CONSISTENT,
            profile=spec["profile"], json_mode=spec["json_mode"],
        )
        _new_file(output_dir / f"REQUEST_{side.upper()}_PRIVATE.json", {
            "schema": SCHEMA, "side": side,
            "pre_review_seal_sha256": seal["pre_review_seal_sha256"],
            "review_prompt_sha256": gate.sha(body),
            "provider": spec["provider"], "model_id": spec["model_id"],
            "status": "BEFORE_TRANSPORT__REQUEST_NOT_PROVEN",
        })
        # A callback is only a synthetic stub. It cannot authenticate itself.
        try:
            observation = transport(side, body)
            if (type(observation) is not dict
                    or observation.get("status") != 200
                    or type(observation.get("provider_request_id")) is not str
                    or not observation["provider_request_id"]
                    or type(observation.get("review")) is not dict):
                raise Hold("TRANSPORT_OBSERVATION_HOLD")
            review = ai.parse_model_response(observation["review"])
            record = {
                "schema": SCHEMA, "side": side,
                "case_sha256": seal["case_sha256"],
                "pre_review_seal_sha256": seal["pre_review_seal_sha256"],
                "provider": spec["provider"], "model_id": spec["model_id"],
                "request_body_sha256": gate.sha(body),
                "review_response_sha256": gate.sha(review),
                "provider_request_id_observed": observation["provider_request_id"],
                "review_decision": review["decision"],
                "receipt_level": "TRANSPORT_OBSERVATION_ONLY__NOT_AUTHENTICATED",
                "provider_execution_independence_verified": False,
                "train_admitted": 0,
            }
        except (ValueError, TypeError, KeyError) as exc:
            # Never leak provider text or response data; preserve attempt record.
            _new_file(output_dir / f"OUTCOME_{side.upper()}_PRIVATE.json", {
                "schema": SCHEMA, "side": side,
                "status": "TRANSPORT_OR_REVIEW_HOLD",
                "train_admitted": 0,
            })
            raise Hold("TRANSPORT_OR_REVIEW_HOLD") from exc
        _new_file(output_dir / f"OUTCOME_{side.upper()}_PRIVATE.json", record)
        seen_sides += 1
    return {
        "schema": SAFE, "status": "SYNTHETIC_TWO_SIDE_LEDGER_COMPLETE__INDEPENDENCE_HOLD",
        "synthetic_side_observations": seen_sides,
        "provider_execution_independence_verified": False,
        "authenticated_provider_evidence": False,
        "private_files_created": 5, "model_requests": 0,
        "gpu_started": False, "train_admitted": 0,
        "private_values_emitted": False,
    }
