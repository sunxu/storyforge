"""R60 REAL1000: synthetic-only reviewer protocol smoke, never opens private files.

Without --execute this performs a pure request-contract preflight. With
--execute it sends a fixed invented story (no private source) once to one
explicitly selected HTTPS/local endpoint. Never logs remote raw responses.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import r60_real_ai_dual_review as reviewer
import r60_real_private_batch as private
import r60_reviewer_transport as transport

SYNTHETIC_PROMPT = (
    '以下JSON是合成测试，不是真实故事：'
    '{"prior_messages":[{"role":"user","content":"我想看看窗外。"},'
    '{"role":"assistant","content":"NPC打开了窗帘。"},'
    '{"role":"user","content":"窗外有什么？"}],'
    '"assistant_target":"NPC说：窗外有一只纸鸟。"}'
)


def inspect(*, endpoint: str, model: str, protocol: str, key_env: str,
            allow_remote: bool, json_mode: bool, execute: bool,
            evidence_dir: Path | None = None) -> dict:
    out = {
        "schema": "storyforge_r60_reviewer_protocol_probe_safe_v1",
        "status": "REVIEWER_PROTOCOL_HOLD",
        "reason_code": "UNVERIFIED",
        "synthetic_only": True,
        "private_source_accessed": False,
        "model_requests": 0,
        "train_admitted": 0,
        "gpu_started": False,
        "private_values_emitted": False,
    }
    try:
        url = reviewer.validate_endpoint(endpoint, allow_remote)
        transport.build_body(
            model=model, prompt=SYNTHETIC_PROMPT,
            instructions=reviewer.REVIEW_INSTRUCTIONS,
            profile=protocol, json_mode=json_mode,
        )
        if not isinstance(model, str) or not model.strip():
            raise ValueError("MODEL_ID_REQUIRED")
        if not execute:
            out.update(status="REVIEWER_PROTOCOL_PREFLIGHT_PASS__NO_REQUEST",
                       reason_code="SYNTHETIC_REQUEST_BUILT")
            return out
        key = os.environ.get(key_env, "")
        # For V2 evidence capture, seal a create-only private attempt BEFORE
        # transport. This path is optional; old probes are unchanged.
        observations = []
        if evidence_dir is not None:
            private.private_dir(evidence_dir, create=True)
            private.write_new(
                evidence_dir / "ATTEMPT_PRIVATE.json",
                json.dumps({
                    "schema": "storyforge_r60_synthetic_probe_observation_v1",
                    "status": "ATTEMPT_CREATED_BEFORE_REQUEST",
                    "model": model, "protocol": protocol,
                    "synthetic_only": True, "train_admitted": 0,
                }, sort_keys=True).encode(),
            )
        # This is the only network call; private source is never loaded.
        out["model_requests"] = 1
        kwargs = {"protocol": protocol, "diagnose_json": True}
        if evidence_dir is not None:
            kwargs["evidence_sink"] = observations.append
        try:
            reviewer.model_request(
                url, model, key, SYNTHETIC_PROMPT,
                120, json_mode, **kwargs,
            )
        finally:
            if evidence_dir is not None:
                private.write_new(
                    evidence_dir / "OUTCOME_PRIVATE.json",
                    json.dumps({
                        "schema": "storyforge_r60_synthetic_probe_observation_v1",
                        "status": "TRANSPORT_OBSERVATION_ONLY__INDEPENDENCE_HOLD",
                        "observations": observations,
                        "provider_execution_independence_verified": False,
                        "train_admitted": 0,
                    }, sort_keys=True).encode(),
                )
        out.update(status="REVIEWER_SYNTHETIC_API_PASS__NO_PRIVATE",
                   reason_code="SCHEMA_VALID")
    except reviewer.Hold as exc:
        safe = {
            "MODEL_TRANSPORT_HOLD", "MODEL_JSON_INVALID",
            "MODEL_ENVELOPE_JSON_INVALID",
            "MODEL_CONTENT_MISSING_OR_NONSTRING",
            "MODEL_CONTENT_JSON_INVALID",
            "MODEL_REVIEW_SCHEMA_INVALID",
            "MODEL_OUTPUT_TRUNCATED",
            "MODEL_REPLY_OVERSIZE", "MODEL_PROTOCOL_HOLD",
            "REVIEW_PROTOCOL_UNSUPPORTED",
            "CLAUDE_PROXY_JSON_MODE_UNSUPPORTED",
            "SEVERE_FLAG_DECISION_INCONSISTENT",
            "QUALITY_FLOOR_DECISION_INCONSISTENT",
            "ENDPOINT_INVALID",
            "REMOTE_REVIEW_REQUIRES_EXPLICIT_HTTPS_OPT_IN",
        } | reviewer.SAFE_HTTP_HOLDS
        out["reason_code"] = (
            str(exc) if str(exc) in safe else "PROBE_RUNTIME_HOLD"
        )
    except ValueError as exc:
        out["reason_code"] = (
            str(exc) if str(exc) in {
                "REVIEW_PROTOCOL_UNSUPPORTED",
                "CLAUDE_PROXY_JSON_MODE_UNSUPPORTED", "MODEL_ID_REQUIRED"
            } else "PROBE_RUNTIME_HOLD"
        )
    except (OSError, TypeError, KeyError, IndexError, AttributeError):
        out["reason_code"] = "PROBE_RUNTIME_HOLD"
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--protocol", required=True,
                        choices=sorted(transport.PROFILES))
    parser.add_argument("--key-env", default=None)
    parser.add_argument("--allow-remote-review", action="store_true")
    parser.add_argument("--json-mode", action="store_true")
    parser.add_argument("--evidence-dir", type=Path, default=None,
                        help="Create-only private 0700 observation directory")
    parser.add_argument("--execute", action="store_true",
                        help="Explicitly issue one synthetic API request")
    args = parser.parse_args()
    report = inspect(
        endpoint=args.endpoint, model=args.model,
        protocol=args.protocol,
        key_env=args.key_env or (
            "R60_CLAUDE_KEY" if args.protocol == "claude-proxy-top-system"
            else "R60_DEEPSEEK_KEY" if args.protocol == "deepseek-chat"
            else "R60_CLAUDE_KEY"
        ),
        allow_remote=args.allow_remote_review,
        json_mode=args.json_mode, execute=args.execute,
        evidence_dir=args.evidence_dir,
    )
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] in {
        "REVIEWER_PROTOCOL_PREFLIGHT_PASS__NO_REQUEST",
        "REVIEWER_SYNTHETIC_API_PASS__NO_PRIVATE",
    } else 42


if __name__ == "__main__":
    sys.exit(main())
