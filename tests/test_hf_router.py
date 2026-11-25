import json

import httpx
import pytest

from storyforge_inference.hf_router import HFRouterClient, RouterHold

MODEL = "org/example"
PROVIDER = "deepinfra"


def make_client(handler):
    return HFRouterClient(
        token="synthetic-token", model=MODEL, provider=PROVIDER, bill_to="synthetic-org",
        response_model="example/model", response_provider="DeepInfra",
        transport=httpx.MockTransport(handler),
    )


def catalog(*, live=True, structured=True):
    return {"data": [{"id": MODEL, "providers": [{
        "provider": PROVIDER, "status": "live" if live else "offline",
        "supports_structured_output": structured,
    }]}]}


def call(client, **extra):
    return client.chat_completion(
        model=MODEL, messages=[{"role": "user", "content": "synthetic"}],
        temperature=0, max_tokens=2048, response_format={"type": "json_schema"},
        **extra,
    )


def test_catalog_and_single_fixed_provider_call():
    seen = []

    def handler(request):
        seen.append(request.method)
        assert request.headers["X-HF-Bill-To"] == "synthetic-org"
        assert request.headers["Authorization"] == "Bearer synthetic-token"
        if request.method == "GET":
            assert request.url.path == "/v1/models"
            return httpx.Response(200, json=catalog())
        assert request.url.path == "/v1/chat/completions"
        body = json.loads(request.content)
        assert body["model"] == MODEL + ":" + PROVIDER
        assert body["stream"] is False
        assert body["reasoning_effort"] == "none"
        return httpx.Response(200, json={
            "model": "example/model", "provider": "DeepInfra",
            "choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}],
        })

    with make_client(handler) as client:
        client.preflight()
        assert call(client, extra_body={"reasoning_effort": "none"}).choices[
            0
        ].message.content == "{}"
        assert client.info["phase"] == "response_received"
    assert seen == ["GET", "POST"]


@pytest.mark.parametrize("live,structured", [(False, True), (True, False)])
def test_unavailable_route_blocks_post(live, structured):
    def handler(request):
        assert request.method == "GET"
        return httpx.Response(200, json=catalog(live=live, structured=structured))

    with make_client(handler) as client:
        with pytest.raises(RouterHold):
            client.preflight()
        with pytest.raises(RouterHold, match="PREFLIGHT_REQUIRED"):
            call(client)


@pytest.mark.parametrize("status", [302, 403, 429, 503])
def test_http_failure_no_retry_or_private_body(status):
    seen = []

    def handler(request):
        seen.append(request.method)
        if request.method == "GET":
            return httpx.Response(200, json=catalog())
        return httpx.Response(status, text="private-body")

    with make_client(handler) as client:
        client.preflight()
        with pytest.raises(RouterHold, match="HF_ROUTER_HTTP_HOLD") as exc:
            call(client)
        assert exc.value.status_code == status
        assert "private-body" not in str(exc.value)
        assert client.info["http_status"] == status
    assert seen == ["GET", "POST"]


@pytest.mark.parametrize("model,provider,finish", [
    ("other/model", "DeepInfra", "stop"),
    ("example/model", "OtherProvider", "stop"),
    ("example/model", "DeepInfra", "length"),
])
def test_wrong_identity_or_truncation_holds(model, provider, finish):
    def handler(request):
        if request.method == "GET":
            return httpx.Response(200, json=catalog())
        return httpx.Response(200, json={
            "model": model, "provider": provider,
            "choices": [{"message": {"content": "{}"}, "finish_reason": finish}],
        })

    with make_client(handler) as client:
        client.preflight()
        with pytest.raises(RouterHold):
            call(client)


def test_transport_error_is_safe():
    def handler(request):
        if request.method == "GET":
            return httpx.Response(200, json=catalog())
        raise httpx.ReadTimeout("private text")

    with make_client(handler) as client:
        client.preflight()
        with pytest.raises(RouterHold, match="TRANSPORT_HOLD"):
            call(client)
        assert client.info["exception_class"] == "ReadTimeout"


def test_length_response_records_only_numeric_usage():
    def handler(request):
        if request.method == "GET":
            return httpx.Response(200, json=catalog())
        return httpx.Response(200, json={
            "model": "example/model", "provider": "DeepInfra",
            "choices": [{"message": {"content": None}, "finish_reason": "length"}],
            "usage": {"prompt_tokens": 500, "completion_tokens": 2048,
                      "total_tokens": 2548, "private": "never log",
                      "completion_tokens_details": {"reasoning_tokens": 2048}},
        })

    with make_client(handler) as client:
        client.preflight()
        with pytest.raises(RouterHold, match="INCOMPLETE_RESPONSE") as exc:
            call(client)
        assert exc.value.status_code == 200
        assert client.info["usage"] == {
            "prompt_tokens": 500, "completion_tokens": 2048, "total_tokens": 2548,
            "reasoning_tokens": 2048,
        }
