"""Shared R59 Source Stage SAFE receipt validation (no private data output)."""
from __future__ import annotations

import re

OLD_SCHEMA = "storyforge-gold-quality-supabase-source-stage-safe-v1"
NEW_SCHEMA = "storyforge-r59-contiguous-suffix-stage-safe-v1"
NEW_STATUS = "CONTIGUOUS_SUFFIX_SOURCE_STAGE_BUILT__NOT_QUALITY_ADMITTED"
HEX = re.compile(r"^[0-9a-f]{64}$")


def valid_staging_receipt(receipt: object, staged_sha: str) -> bool:
    if not isinstance(receipt, dict) or HEX.fullmatch(staged_sha or "") is None:
        return False
    if receipt.get("staged_file_sha256") != staged_sha:
        return False
    schema = receipt.get("schema")
    if schema == OLD_SCHEMA:
        return receipt.get("status") == "GOLD_SOURCE_CONTEXT_STAGED__QUALITY_REVIEW_PENDING"
    if schema == NEW_SCHEMA:
        return (
            receipt.get("status") == NEW_STATUS
            and receipt.get("context_structure_hold") == 0
            and receipt.get("context_staged") == receipt.get("source_rows")
            and isinstance(receipt.get("source_rows"), int)
            and receipt["source_rows"] > 0
            and receipt.get("source_histories_mutated") is False
            and receipt.get("original_staging_mutated") is False
            and receipt.get("quality_v1_admitted") == 0
            and receipt.get("training_authorized") is False
            and receipt.get("gpu_started") is False
            and HEX.fullmatch(receipt.get("source_context_file_sha256") or "") is not None
            and HEX.fullmatch(receipt.get("previous_staged_file_sha256") or "") is not None
        )
    return False
