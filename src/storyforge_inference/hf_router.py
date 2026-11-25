"""HF Router transport independent of legacy Hub provider mapping."""
from __future__ import annotations

import re
from types import SimpleNamespace
from typing import Any

import httpx

BASE = "https://router.huggingface.co/v1"
FINISH_REASONS = {"stop", "length", "content_filter", "tool_calls", "error"}
IDENTIFIER = re.compile(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?\Z")


class RouterHold(RuntimeError):
    """Safe reason code only; never exposes request or response bodies."""

    def __init__(self, code: str, status: int | None = None):
        super().__init__(code)
        self.status_code = status


class HFRouterClient:
    """Fixed model/provider/organization; no fallback or application retries."""

    def __init__(
        self, *, token: str, model: str, provider: str, bill_to: str,
        response_model: str, response_provider: str, timeout: float = 120,
        transport: httpx.BaseTransport | None = None,
    ):
        values = (model, provider, bill_to, response_model)
        if not all(isinstance(v, str) and IDENTIFIER.fullmatch(v) for v in values):
            raise RouterHold("HF_ROUTER_IDENTITY_HOLD")
        if not token or not token.strip() or not response_provider.strip():
            raise RouterHold("HF_ROUTER_CREDENTIALS_HOLD")
        self.model = model
        self.provider = provider
        self.response_model = response_model
        self.response_provider = response_provider
        self.info: dict[str, Any] = {"phase": "initialized"}
        self._ready = False
        self._client = httpx.Client(
            headers={"Authorization": "Bearer " + token, "X-HF-Bill-To": bill_to},
            timeout=timeout, follow_redirects=False,
            transport=transport if transport is not None else httpx.HTTPTransport(retries=0),
        )

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._client.close()

    def _request(self, method: str, path: str, **kwargs):
        self.info = {"phase": "request_started", "method": method}
        try:
            response = self._client.request(method, BASE + path, **kwargs)
        except httpx.HTTPError as exc:
            self.info.update(phase="transport_error", exception_class=type(exc).__name__)
            raise RouterHold("HF_ROUTER_TRANSPORT_HOLD") from None
        self.info["http_status"] = response.status_code
        if response.status_code != 200:
            self.info["phase"] = "http_error"
            raise RouterHold("HF_ROUTER_HTTP_HOLD", response.status_code)
        try:
            data = response.json()
        except ValueError:
            self.info["phase"] = "invalid_envelope"
            raise RouterHold("HF_ROUTER_JSON_HOLD") from None
        if not isinstance(data, dict):
            raise RouterHold("HF_ROUTER_ENVELOPE_HOLD")
        return data

    def preflight(self) -> dict:
        """GET only; directory capability, not proof of billing or inference."""
        self._ready = False
        data = self._request("GET", "/models")
        models = data.get("data")
        if not isinstance(models, list):
            raise RouterHold("HF_ROUTER_CATALOG_HOLD")
        matches = [m for m in models if isinstance(m, dict) and m.get("id") == self.model]
        providers = matches[0].get("providers") if len(matches) == 1 else None
        if not isinstance(providers, list):
            raise RouterHold("HF_ROUTER_MODEL_UNAVAILABLE_HOLD")
        routes = [
            p for p in providers if isinstance(p, dict) and p.get("provider") == self.provider
        ]
        if len(routes) != 1 or routes[0].get("status") != "live":
            raise RouterHold("HF_ROUTER_PROVIDER_UNAVAILABLE_HOLD")
        route = routes[0]
        if route.get("supports_structured_output") is not True:
            raise RouterHold("HF_ROUTER_STRUCTURED_OUTPUT_HOLD")
        self._ready = True
        self.info = {"phase": "catalog_verified", "http_status": 200}
        return {
            "model": self.model, "provider": self.provider,
            "context_length": route.get("context_length"), "pricing": route.get("pricing"),
        }

    def chat_completion(
        self, *, model: str, messages: list[dict], temperature: float,
        max_tokens: int, response_format: dict, extra_body: dict | None = None,
    ) -> Any:
        if not self._ready:
            raise RouterHold("HF_ROUTER_PREFLIGHT_REQUIRED_HOLD")
        if model != self.model:
            raise RouterHold("HF_ROUTER_MODEL_MISMATCH_HOLD")
        # Only explicitly supplied reasoning controls can extend the request.
        if extra_body is not None and (
            not isinstance(extra_body, dict)
            or set(extra_body) - {"reasoning_effort", "thinking"}
        ):
            raise RouterHold("HF_ROUTER_EXTRA_BODY_HOLD")
        body = {
            **(extra_body or {}), "model": self.model + ":" + self.provider,
            "messages": messages, "temperature": temperature, "max_tokens": max_tokens,
            "response_format": response_format, "stream": False,
        }
        data = self._request("POST", "/chat/completions", json=body)
        if (data.get("model") != self.response_model
                or str(data.get("provider", "")).casefold() != self.response_provider.casefold()):
            self.info["phase"] = "response_identity_mismatch"
            raise RouterHold("HF_ROUTER_RESPONSE_IDENTITY_HOLD")
        # Whitelist numerical usage only; never retain hidden reasoning or raw payloads.
        usage = data.get("usage")
        if isinstance(usage, dict):
            safe_usage = {
                key: usage[key] for key in ("prompt_tokens", "completion_tokens", "total_tokens")
                if type(usage.get(key)) is int and usage[key] >= 0
            }
            details = usage.get("completion_tokens_details")
            if isinstance(details, dict):
                reasoning = details.get("reasoning_tokens")
                if type(reasoning) is int and reasoning >= 0:
                    safe_usage["reasoning_tokens"] = reasoning
            self.info["usage"] = safe_usage
        try:
            choice = data["choices"][0]
            content = choice["message"]["content"]
            finish = choice["finish_reason"]
        except (KeyError, IndexError, TypeError):
            raise RouterHold("HF_ROUTER_CHOICE_HOLD") from None
        self.info.update(
            phase="response_received",
            finish_reason=finish if isinstance(finish, str) and finish in FINISH_REASONS else None,
            content_chars=len(content) if isinstance(content, str) else None,
        )
        if finish != "stop" or not isinstance(content, str) or not content.strip():
            raise RouterHold("HF_ROUTER_INCOMPLETE_RESPONSE_HOLD", 200)
        return SimpleNamespace(choices=[SimpleNamespace(
            message=SimpleNamespace(content=content), finish_reason=finish,
        )])
