"""Gold48 J1 direct DeepSeek adapter; J2 and the frozen judge stay unchanged.

Reuses historical R60 deepseek-chat request protocol and Gold48 step ledger.
The immutable execution revision is prepared without an API call; --execute is
one explicit paid call, with no SDK retry and no unblinding.
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from .gold48_blind import private_input
from .gold48_hf_judge import JudgeHold, response_schema
from .gold48_judge_lock import LockHold, digest, require
from .gold48_judge_step import read_locked_packet, step
from .hf_blind_stage import write_once
from .hf_literary_review import canonical

MODEL = "deepseek-flash"
API_ORIGIN = "https://api.deepseek.com"
API_ENDPOINT = API_ORIGIN + "/chat/completions"
REVISION_NAME = "GOLD48_J1_OFFICIAL_REVISION_PRIVATE.json"
REVISION_SCHEMA = "storyforge_r60_gold48_j1_official_revision_private_v1"
MAX_RESPONSE_BYTES = 120_000


class OfficialProviderError(Exception):
    """Only structural, non-private error information is retained."""

    def __init__(self, http_status: int | None = None) -> None:
        super().__init__("OFFICIAL_PROVIDER_REQUEST_HOLD")
        self.status_code = http_status


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class OfficialDeepSeekClient:
    """HF-shaped chat_completion facade over the proven R60 DeepSeek protocol."""

    def __init__(self, key: str) -> None:
        require(type(key) is str and bool(key), "DEEPSEEK_KEY_MISSING_HOLD")
        self._key = key

    def chat_completion(
        self, *, model: str, messages: list[dict],
        temperature: int | float, max_tokens: int, response_format: dict,
        extra_body: dict,
    ) -> Any:
        require(
            model == MODEL and temperature == 0
            and type(max_tokens) is int and 128 <= max_tokens <= 4096
            and type(messages) is list and len(messages) == 2
            and [m.get("role") for m in messages] == ["system", "user"]
            and all(type(m.get("content")) is str for m in messages)
            and type(response_format) is dict
            and response_format.get("type") == "json_schema"
            and type(response_format.get("json_schema")) is dict
            and response_format["json_schema"].get("schema") == response_schema()
            and extra_body == {"thinking": {"type": "disabled"}},
            "J1_OFFICIAL_REQUEST_PARAMETERS_HOLD",
        )
        # Reuse the historical QD20/R60 transport profile; only the JSON Schema
        # delivery is adapted because DeepSeek officially supports json_object.
        from experiments.r58_quality.r60_reviewer_transport import build_body

        instructions = (
            messages[0]["content"]
            + "\n只返回一个有效的JSON对象，字段必须严格符合以下JSON Schema；"
            + "不要添加任何额外键，不要使用Markdown或代码围栏：\n"
            + canonical(response_schema()).decode("utf-8")
        )
        body = build_body(
            model=MODEL, prompt=messages[1]["content"],
            instructions=instructions, profile="deepseek-chat",
            json_mode=True,
        )
        body["max_tokens"] = max_tokens
        wire = canonical(body)
        request = urllib.request.Request(
            API_ENDPOINT,
            data=wire,
            headers={
                "Authorization": "Bearer " + self._key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        # Historical R60 safety behavior: one POST, no redirects or ambient proxy.
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), NoRedirect
        )
        try:
            with opener.open(request, timeout=180) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        except urllib.error.HTTPError as exc:
            raise OfficialProviderError(
                exc.code if type(exc.code) is int else None
            ) from None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            raise OfficialProviderError() from None
        if len(raw) > MAX_RESPONSE_BYTES:
            raise OfficialProviderError() from None
        try:
            envelope = json.loads(raw)
            choice = envelope["choices"][0]
            finish_reason = choice["finish_reason"]
            content = choice["message"]["content"]
            if type(content) is not str:
                raise TypeError("non-text completion")
        except (KeyError, ValueError, TypeError, IndexError, UnicodeError):
            raise OfficialProviderError() from None
        return SimpleNamespace(choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
                finish_reason=finish_reason,
            )
        ])


def make_client(*, hf_token: str, fixed_provider: str) -> OfficialDeepSeekClient:
    require(fixed_provider == "deepseek-official",
            "J1_OFFICIAL_PROVIDER_IDENTITY_HOLD")
    return OfficialDeepSeekClient(hf_token)


def paths(root: Path) -> tuple[Path, Path, Path]:
    require(root.is_absolute() and root.name == "gold48-quality-v1-blind-20261122",
            "J1_OFFICIAL_ROOT_HOLD")
    return (
        root / "reviewers/GOLD48_BLIND_240_PRIVATE.jsonl",
        root / "owner/GOLD48_JUDGE_LOCK_PRIVATE.json",
        root / "owner" / REVISION_NAME,
    )


def prepare(root: Path) -> dict:
    packet, lock_path, revision_path = paths(root)
    require(not revision_path.exists() and not revision_path.is_symlink(),
            "J1_OFFICIAL_REVISION_ALREADY_EXISTS_HOLD")
    lock, _ = read_locked_packet(packet, lock_path)
    j1 = lock["config"]["reviewers"][0]
    require(
        j1["reviewer_id"] == "J1"
        and j1["model"] == "deepseek-ai/DeepSeek-V4.1-Flash"
        and j1["provider"] == "fireworks-ai",
        "J1_FROZEN_REVIEWER_MISMATCH_HOLD",
    )
    revision = {
        "schema": REVISION_SCHEMA,
        "status": "J1_OFFICIAL_REVISION_PREPARED__NO_EXTERNAL_CALLS",
        "reviewer_id": "J1",
        "lock_sha256": digest(private_input(lock_path, limit=65536)),
        "frozen_judge_sha256": lock["judge_source_sha256"],
        "frozen_model": j1["model"],
        "frozen_provider": j1["provider"],
        "actual_model": MODEL,
        "model_version": "DeepSeek-V4.1-Flash-1017",
        "actual_provider": "deepseek-official",
        "api_origin": API_ORIGIN,
        "response_format": "json_object",
        "thinking": "disabled",
        "underlying_model_version_may_differ": True,
        "score_rubric_changed": False,
        "owner_mapping_accessed": False,
        "private_values_emitted": False,
    }
    write_once(revision_path, canonical(revision) + b"\n")
    return {
        "status": revision["status"],
        "reviewer_id": "J1", "external_calls": 0,
        "owner_mapping_accessed": False,
        "private_values_emitted": False,
    }


def run_one(root: Path, position: int, *, key: str) -> dict:
    packet, lock_path, revision_path = paths(root)
    return step(
        packet=packet, lock_path=lock_path,
        output_dir=root / "reviews/J1",
        reviewer_id="J1", position=position,
        approve_private_transfer=True,
        approve_paid_calls=True,
        confirm_hf_spending_cap=False,
        hf_token=key, client_factory=make_client,
        official_revision=revision_path,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--position", type=int)
    parser.add_argument("--approve-private-transfer", action="store_true")
    parser.add_argument("--approve-paid-calls", action="store_true")
    args = parser.parse_args()
    try:
        if args.prepare:
            require(args.position is None, "J1_PREPARE_POSITION_HOLD")
            result = prepare(args.root)
        else:
            require(
                args.position is not None
                and args.approve_private_transfer is True
                and args.approve_paid_calls is True,
                "J1_OFFICIAL_EXECUTION_NOT_AUTHORIZED_HOLD",
            )
            result = run_one(
                args.root, args.position,
                key=os.environ.get("R60_DEEPSEEK_KEY", ""),
            )
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    except (LockHold, JudgeHold, ValueError, OSError, OfficialProviderError) as exc:
        code = (
            str(exc) if isinstance(exc, (LockHold, JudgeHold))
            else "J1_OFFICIAL_INPUT_OR_EXECUTION_HOLD"
        )
        print(json.dumps({
            "status": "GOLD48_J1_OFFICIAL_HOLD", "reason": code,
            "private_values_emitted": False, "quality_v1_admitted": 0,
        }, sort_keys=True))
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
