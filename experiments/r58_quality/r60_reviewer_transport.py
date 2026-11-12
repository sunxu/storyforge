"""Protocol-only profiles for R60 literary reviewers.

No network, secrets, database, private storage or business decisions.
Keep scoring and receipt ownership in r60_real_ai_dual_review / Quality Pipeline.
"""
from __future__ import annotations

PROFILES = frozenset({"openai-chat", "claude-proxy-top-system", "deepseek-chat"})


def require_profile(profile: str) -> str:
    if not isinstance(profile, str) or profile not in PROFILES:
        raise ValueError("REVIEW_PROTOCOL_UNSUPPORTED")
    return profile


def build_body(*, model: str, prompt: str, instructions: str,
               profile: str, json_mode: bool) -> dict:
    """Construct an isolated request, never embedding another reviewer's output."""
    require_profile(profile)
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1600,
        "stream": False,
    }
    if profile == "claude-proxy-top-system":
        # Historical 4Router Claude endpoint rejected messages[0].role=system.
        body["system"] = instructions
        # Do not force temperature or unsupported JSON-mode on this proxy.
        if json_mode:
            raise ValueError("CLAUDE_PROXY_JSON_MODE_UNSUPPORTED")
    else:
        body["messages"].insert(0, {"role": "system", "content": instructions})
        if profile == "openai-chat":
            # Preserve the historical generic client behavior.
            body["temperature"] = 0
        # DeepSeek protocol is not assumed to share Qwen Thinking settings.
        if json_mode:
            body["response_format"] = {"type": "json_object"}
    return body
