"""R60 forward-only *candidate* Reviewer V2. No legacy receipt modifications.

Uses existing Qwen/DeepSeek API client and frozen V3 rubric. Candidate/source
attestations must come from independently reviewed private evidence. A Boolean
in the input is NOT independent proof; this runner never admits training.
No API requests unless explicit --execute and --allow-remote-private-review.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import r60_forward_evidence_gate_v1 as gate
import r60_forward_reviewer_v2_ledger as ledger
import r60_real_ai_dual_review as ai
import r60_real_private_batch as private

SCHEMA = "storyforge_r60_forward_official_review_v2_safe_v1"
INPUT_SCHEMA = "storyforge_r60_forward_official_review_input_private_v1"
CONFIGS = (
    ("a", "qwen", "qwen3.7-flash", "openai-chat",
     "https://dashscope.aliyuncs.com/compatible-mode/v1", "DASHSCOPE_API_KEY"),
    ("b", "deepseek", "deepseek-flash", "deepseek-chat",
     "https://api.deepseek.com", "R60_DEEPSEEK_KEY"),
)


class Hold(ValueError):
    pass


def validated_bundle(bundle: object) -> tuple[dict, dict, str]:
    if type(bundle) is not dict or bundle.get("schema") != INPUT_SCHEMA:
        raise Hold("BUNDLE_SCHEMA_HOLD")
    if set(bundle) != {"schema", "source", "protection", "world", "case"}:
        raise Hold("BUNDLE_KEYS_HOLD")
    case = bundle["case"]
    if type(case) is not dict or set(case) != {
        "history_messages", "target_text",
    }:
        raise Hold("CASE_KEYS_HOLD")
    # Never accept an unchecked source-declared history hash as evidence.
    source = bundle["source"]
    if type(source) is not dict or (
        source.get("history_sha256") != private.digest(case["history_messages"])
        or source.get("target_sha256") != private.digest(case["target_text"])
        or source.get("case_sha256") != private.digest(case)
    ):
        raise Hold("SOURCE_CONTENT_BINDING_HOLD")
    seal = gate.require_pre_review(
        source, bundle["protection"], bundle["world"])
    prompt = ai.prompt_for_case(case)
    return seal, case, prompt


def run(
    bundle: dict, output_dir: Path, *, execute: bool,
    allow_remote_private_review: bool, model_request=None,
) -> dict:
    seal, _case, prompt = validated_bundle(bundle)
    if output_dir.parent != private.BASE or output_dir.is_symlink():
        raise Hold("PRIVATE_DESTINATION_HOLD")
    if output_dir.exists():
        raise Hold("CREATE_ONLY_HOLD")
    if not execute:
        return {
            "schema": SCHEMA, "status": "FORWARD_OFFICIAL_V2_PREFLIGHT__NO_REQUEST",
            "pre_review_contract_bound": True,
            "source_and_eval_independently_authenticated": False,
            "model_requests": 0, "train_admitted": 0,
            "gpu_started": False, "private_values_emitted": False,
        }
    if not allow_remote_private_review:
        raise Hold("REMOTE_REVIEW_OPT_IN_REQUIRED_HOLD")
    # Credentials are intentionally checked only AFTER pre-review evidence.
    for _, _, _, _, _, env in CONFIGS:
        if not os.getenv(env):
            raise Hold("REVIEW_KEY_MISSING_HOLD")
    private.private_dir(output_dir, create=True)
    ledger._new_file(output_dir / "PRE_REVIEW_SEAL_PRIVATE.json", seal)
    request = model_request or ai.model_request
    completed = 0
    attempts = 0
    for side, provider, model, profile, base_url, env in CONFIGS:
        url = ai.validate_endpoint(base_url, True)
        body = ledger.protocol.build_body(
            model=model, prompt=prompt,
            instructions=ai.REVIEW_INSTRUCTIONS_V3_CONSISTENT,
            profile=profile, json_mode=True,
        )
        ledger._new_file(output_dir / f"REQUEST_{side.upper()}_PRIVATE.json", {
            "schema": SCHEMA, "side": side, "provider": provider,
            "model_id": model, "pre_review_seal_sha256":
                seal["pre_review_seal_sha256"],
            "request_body_sha256": gate.sha(body),
            "status": "CREATED_BEFORE_NETWORK__REQUEST_UNCONFIRMED",
        })
        attempts += 1
        observations = []
        decision = None
        error = None
        try:
            result = request(
                url, model, os.environ[env], prompt, 120, True,
                protocol=profile,
                instructions=ai.REVIEW_INSTRUCTIONS_V3_CONSISTENT,
                diagnose_json=True, evidence_sink=observations.append,
            )
            result = ai.parse_model_response(result)
            decision = result["decision"]
        except (ai.Hold, ValueError, TypeError) as exc:
            # Never output private response text or arbitrary exception messages.
            error = (str(exc) if type(exc) is ai.Hold and str(exc) in {
                "MODEL_JSON_INVALID", "MODEL_CONTENT_JSON_INVALID",
                "MODEL_REVIEW_SCHEMA_INVALID",
                "QUALITY_FLOOR_DECISION_INCONSISTENT",
                "SEVERE_FLAG_DECISION_INCONSISTENT",
            } else "REVIEW_TRANSPORT_OR_RESPONSE_HOLD")
        ledger._new_file(output_dir / f"OUTCOME_{side.upper()}_PRIVATE.json", {
            "schema": SCHEMA, "side": side,
            "pre_review_seal_sha256": seal["pre_review_seal_sha256"],
            "status": (
                "OBSERVED_UNAUTHENTICATED__REVIEW_HOLD" if error
                else "OBSERVED_UNAUTHENTICATED__REVIEW_RECORDED"
            ),
            "reason_code": error,
            "review_decision": decision,
            "observations": observations,
            "provider_evidence_authenticated": False,
            "train_admitted": 0,
        })
        if error:
            break
        completed += 1
    return {
        "schema": SCHEMA,
        "status": "FORWARD_OFFICIAL_V2_EXECUTED__INDEPENDENCE_HOLD",
        "attempted_reviewers": attempts,
        "schema_valid_reviews": completed,
        "provider_execution_independence_verified": False,
        "source_and_eval_independently_authenticated": False,
        "model_requests": attempts, "train_admitted": 0,
        "gpu_started": False, "private_values_emitted": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--execute", action="store_true")
    p.add_argument("--allow-remote-private-review", action="store_true")
    args = p.parse_args()
    try:
        if args.input.parent != private.BASE:
            raise Hold("PRIVATE_SOURCE_PATH_HOLD")
        raw = private.read_private(args.input, 120_000)
        out = run(
            json.loads(raw), args.output_dir, execute=args.execute,
            allow_remote_private_review=args.allow_remote_private_review,
        )
        print(json.dumps(out, sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - never print private payloads/paths/errors
        print(json.dumps({
            "schema": SCHEMA, "status": "FORWARD_OFFICIAL_V2_HOLD",
            "train_admitted": 0, "gpu_started": False,
            "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    sys.exit(main())
