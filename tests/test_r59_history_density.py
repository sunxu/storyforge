from __future__ import annotations

import hashlib
import json

import pytest

from experiments.r59_history_density.r59_history_density import build_report, load_rows

FINGERPRINT = "a" * 64
SCHEMA = "storyforge-r59-semantic-review-prompt-private-v1"


def make_rows() -> list[dict]:
    return [
        {
            "schema": SCHEMA,
            "pilot_index": index,
            "prompt_fingerprint": FINGERPRINT,
            "review_decision": None,
            "gpu_started": False,
            "quality_v1_admitted": False,
            "messages": [
                {"role": "system", "content": "S" * 4},
                {"role": "user", "content": "U" * (100 + index)},
            ],
            "history_coverage": {
                "scope": "FULL_STAGED_SUFFIX_ONLY",
                "retained_history_messages": index + 1,
                "removed_upstream_prefix_messages": index * 2,
                "context_semantically_verified": True,
                "historical_world_card_approved": False,
                "history_origin_verified_from_database": True,
            },
        }
        for index in range(8)
    ]


def encode_rows(rows: list[dict]) -> bytes:
    return b"\n".join(json.dumps(row).encode() for row in rows)


def test_aggregate_has_no_prompt_text_and_no_training_admission():
    raw = encode_rows(make_rows())
    rows = load_rows(raw, hashlib.sha256(raw).hexdigest(), FINGERPRINT)
    report = build_report(rows, hashlib.sha256(raw).hexdigest(), None)
    assert report["aggregate"]["retained_history_messages_total"] == 36
    assert report["aggregate"]["removed_upstream_prefix_messages_total"] == 56
    assert report["cases"][2]["serialized_user_prompt_chars"] == 102
    assert "UUUU" not in json.dumps(report)
    assert report["gpu_started"] is False
    assert report["training_performed"] is False
    assert report["quality_v1_admitted"] == 0


def test_rejects_source_hash_mismatch():
    raw = encode_rows(make_rows())
    with pytest.raises(ValueError, match="SOURCE_SHA256_MISMATCH"):
        load_rows(raw, "0" * 64, FINGERPRINT)


def test_rejects_wrong_case_count():
    raw = json.dumps(make_rows()[0]).encode()
    with pytest.raises(ValueError, match="INPUT_CASE_COUNT_INVALID"):
        load_rows(raw, hashlib.sha256(raw).hexdigest(), FINGERPRINT)


def test_rejects_wrong_case_order():
    rows = make_rows()
    rows[0]["pilot_index"] = 1
    raw = encode_rows(rows)
    with pytest.raises(ValueError, match="PROMPT_IDENTITY_INVALID_CASE_0"):
        load_rows(raw, hashlib.sha256(raw).hexdigest(), FINGERPRINT)


def test_rejects_missing_history_count():
    rows = make_rows()
    del rows[0]["history_coverage"]["retained_history_messages"]
    raw = encode_rows(rows)
    with pytest.raises(ValueError, match="HISTORY_COVERAGE_FIELD_INVALID"):
        load_rows(raw, hashlib.sha256(raw).hexdigest(), FINGERPRINT)


def test_rejects_negative_history_count():
    rows = make_rows()
    rows[0]["history_coverage"]["removed_upstream_prefix_messages"] = -1
    raw = encode_rows(rows)
    with pytest.raises(ValueError, match="HISTORY_COVERAGE_FIELD_INVALID"):
        load_rows(raw, hashlib.sha256(raw).hexdigest(), FINGERPRINT)


def test_rejects_wrong_history_scope():
    rows = make_rows()
    rows[0]["history_coverage"]["scope"] = "OTHER"
    raw = encode_rows(rows)
    with pytest.raises(ValueError, match="HISTORY_COVERAGE_SCOPE_INVALID"):
        load_rows(raw, hashlib.sha256(raw).hexdigest(), FINGERPRINT)
