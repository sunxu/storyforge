"""Synthetic-only protocol tests for the direct J1 official DeepSeek facade."""
from __future__ import annotations

import json
import unittest
import urllib.request
from unittest.mock import patch

from storyforge_gold_quality.gold48_hf_judge import response_schema
from storyforge_gold_quality.gold48_j1_official import (
    API_ENDPOINT,
    NoRedirect,
    OfficialDeepSeekClient,
)


class FakeHTTPResponse:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit):
        assert limit <= 120001
        return json.dumps({
            "choices": [{
                "finish_reason": "stop",
                "message": {"content": '{"scores": {}}'},
            }]
        }).encode()


class FakeOpener:
    def __init__(self):
        self.requests = []

    def open(self, request, timeout):
        self.requests.append((request, timeout))
        return FakeHTTPResponse()


class DeepSeekOfficialProtocolTest(unittest.TestCase):
    def test_official_direct_protocol_reuses_existing_deepseek_chat(self) -> None:
        opener = FakeOpener()
        handlers = []
        def fake_opener(*args):
            handlers.extend(args)
            return opener

        with patch("urllib.request.build_opener", side_effect=fake_opener):
            client = OfficialDeepSeekClient("synthetic-token")
            r = client.chat_completion(
                model="deepseek-flash",
                messages=[
                    {"role": "system", "content": "synthetic rubric"},
                    {"role": "user", "content": "synthetic private prompt"},
                ],
                temperature=0, max_tokens=2048,
                response_format={
                    "type": "json_schema",
                    "json_schema": {"schema": response_schema()},
                },
                extra_body={"thinking": {"type": "disabled"}},
            )
        self.assertEqual(r.choices[0].finish_reason, "stop")
        self.assertEqual(r.choices[0].message.content, '{"scores": {}}')
        self.assertEqual(len(opener.requests), 1)
        request, timeout = opener.requests[0]
        self.assertEqual(request.full_url, API_ENDPOINT)
        self.assertEqual(timeout, 180)
        self.assertTrue(any(type(h) is urllib.request.ProxyHandler
                            for h in handlers))
        self.assertTrue(any(h is NoRedirect or isinstance(h, NoRedirect)
                            for h in handlers))
        sent = json.loads(request.data)
        self.assertEqual(sent["model"], "deepseek-flash")
        self.assertEqual(sent["response_format"], {"type": "json_object"})
        self.assertEqual(sent["thinking"], {"type": "disabled"})
        self.assertEqual(sent["temperature"], 0)
        self.assertEqual(sent["max_tokens"], 2048)
        self.assertEqual(sent["messages"][1]["content"],
                         "synthetic private prompt")
        self.assertIn('"scores"', sent["messages"][0]["content"])

    def test_unexpected_model_or_mode_rejected_without_network(self) -> None:
        client = OfficialDeepSeekClient("synthetic-token")
        common = {
            "messages": [
                {"role": "system", "content": "synthetic rubric"},
                {"role": "user", "content": "synthetic prompt"},
            ],
            "temperature": 0,
            "max_tokens": 2048,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"schema": response_schema()},
            },
            "extra_body": {"thinking": {"type": "disabled"}},
        }
        with patch("urllib.request.build_opener") as opener:
            with self.assertRaisesRegex(
                ValueError, "J1_OFFICIAL_REQUEST_PARAMETERS_HOLD"
            ):
                client.chat_completion(model="deepseek-v4-pro", **common)
            with self.assertRaisesRegex(
                ValueError, "J1_OFFICIAL_REQUEST_PARAMETERS_HOLD"
            ):
                client.chat_completion(
                    model="deepseek-flash",
                    **{**common, "extra_body": {"thinking": {"type": "enabled"}}},
                )
            opener.assert_not_called()


if __name__ == "__main__":
    unittest.main()
