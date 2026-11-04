"""Rebuild R59 source staging from verified, untouched contiguous suffixes.

Source and existing staging are read-only. All outputs are new private files.
Structural staging is NOT Quality-v1 admission, semantic approval or training.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from gold_source_context_stage import (
    MAX_INPUT_BYTES,
    StageHold,
    _create_only,
    _private_file,
    _read_rows,
    stage_source,
)
from quality_v1 import canonical, sha
from r59_contiguous_suffix_probe import _valid

SCHEMA = "storyforge-r59-contiguous-suffix-stage-safe-v1"


def rebuild(source_rows: list[dict], old_rows: list[dict], system: str):
    if not isinstance(source_rows, list) or not source_rows:
        raise StageHold("SOURCE_ROWS_INVALID")
    if not isinstance(old_rows, list) or len(source_rows) != len(old_rows):
        raise StageHold("STAGED_ROW_COUNT_MISMATCH")
    old_index = {r["case_id"]: r for r in old_rows}
    if len(old_index) != len(old_rows):
        raise StageHold("STAGED_IDENTITY_DUPLICATE")
    projected = []
    provenance = {}
    for row in source_rows:
        cid = row["case_id"]
        previous = old_index.get(cid)
        if previous is None or previous.get("target_sha256") != row.get("target_sha256"):
            raise StageHold("STAGED_TARGET_IDENTITY_MISMATCH")
        history = row.get("history")
        if not isinstance(history, list) or not history:
            raise StageHold("HISTORY_MISSING")
        if not _valid(history[-1]) or history[-1]["role"] != "user":
            raise StageHold("FINAL_USER_NOT_VALID")
        index = len(history) - 1
        expected = "assistant"
        while index > 0 and _valid(history[index - 1]) and history[index - 1]["role"] == expected:
            index -= 1
            expected = "user" if expected == "assistant" else "assistant"
        suffix = history[index:]
        if len(suffix) < 2:
            raise StageHold("SUFFIX_CONTEXT_TOO_SHORT")
        # The proposed change is a strict suffix only: no middle deletion.
        if suffix != history[index:] or suffix[-1] != history[-1]:
            raise StageHold("SUFFIX_IDENTITY_INVALID")
        projected.append({**row, "history": suffix})
        provenance[cid] = {
            "source_history_sha256": sha(canonical(history)),
            "source_history_messages": len(history),
            "retained_history_messages": len(suffix),
            "prefix_messages_excluded": index,
            "retained_suffix_sha256": sha(canonical(suffix)),
            "selection_policy": "LONGEST_COMPLETED_NONBLANK_ALTERNATING_SUFFIX",
            "temporal_or_semantic_validity_proven": False,
        }
    output, safe = stage_source(projected, system)
    if safe["context_staged"] != len(source_rows):
        raise StageHold("SUFFIX_STAGE_NOT_ALL_VALID")
    prefix = Counter()
    for row in output:
        if row["status"] != "SOURCE_CONTEXT_STAGED__QUALITY_REVIEW_PENDING":
            raise StageHold("REBUILT_ROW_NOT_STAGED")
        cid = row["case_id"]
        previous = old_index[cid]
        if previous.get("status") == "SOURCE_CONTEXT_STAGED__QUALITY_REVIEW_PENDING":
            if row["input_messages_sha256"] != previous.get("input_messages_sha256"):
                raise StageHold("ORIGINAL_READY_ROW_CHANGED")
            prefix["unchanged_original_ready"] += 1
        else:
            if previous.get("status") != "SOURCE_STRUCTURE_HOLD":
                raise StageHold("PREVIOUS_STATUS_UNKNOWN")
            prefix["recovered_from_structure_hold"] += 1
        row["history_suffix_provenance"] = provenance[cid]
    safe.update({
        "schema": SCHEMA,
        "status": "CONTIGUOUS_SUFFIX_SOURCE_STAGE_BUILT__NOT_QUALITY_ADMITTED",
        "original_ready_unchanged": prefix["unchanged_original_ready"],
        "previously_held_now_structurally_staged": prefix["recovered_from_structure_hold"],
        "prefix_removed_candidates": sum(v["prefix_messages_excluded"] > 0 for v in provenance.values()),
        "total_prefix_messages_excluded": sum(v["prefix_messages_excluded"] for v in provenance.values()),
        "source_histories_mutated": False,
        "original_staging_mutated": False,
        "temporal_or_semantic_validity_proven": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "r50_accessed": False,
        "private_values_emitted": False,
    })
    return output, safe


def run(source: Path, prior_stage: Path, prior_safe: Path, outdir: Path):
    raw_source = _private_file(source, MAX_INPUT_BYTES)
    raw_prior = _private_file(prior_stage, MAX_INPUT_BYTES)
    safe_raw = _private_file(prior_safe, 64 * 1024)
    safe = json.loads(safe_raw)
    if (
        hashlib.sha256(raw_source).hexdigest() != safe.get("source_context_file_sha256")
        or hashlib.sha256(raw_prior).hexdigest() != safe.get("staged_file_sha256")
    ):
        raise StageHold("SOURCE_OR_STAGE_PIN_MISMATCH")
    originals = _read_rows(raw_source)
    staged = _read_rows(raw_prior)
    ready = [r for r in staged if r.get("status") == "SOURCE_CONTEXT_STAGED__QUALITY_REVIEW_PENDING"]
    if not ready:
        raise StageHold("NO_SYSTEM_CONTEXT_TO_REUSE")
    messages = ready[0].get("messages")
    if not isinstance(messages, list) or not messages or messages[0].get("role") != "system":
        raise StageHold("SYSTEM_NOT_FOUND")
    system = messages[0].get("content")
    if not isinstance(system, str) or sha(system.encode("utf-8")) != safe.get("system_prompt_sha256"):
        raise StageHold("SYSTEM_PIN_MISMATCH")
    if any(r.get("messages", [None])[0] != messages[0] for r in ready):
        raise StageHold("SYSTEM_INCONSISTENT")
    result, output_safe = rebuild(originals, staged, system)
    if outdir.exists() or outdir.is_symlink():
        raise StageHold("OUTPUT_EXISTS")
    if outdir.resolve().is_relative_to(Path.cwd().resolve()):
        raise StageHold("OUTPUT_IN_REPO")
    if (
        not outdir.parent.is_dir() or outdir.parent.is_symlink()
        or (outdir.parent.stat().st_mode & 0o777) != 0o700
    ):
        raise StageHold("OUTPUT_PARENT_INVALID")
    outdir.mkdir(mode=0o700)
    try:
        payload = b"".join(canonical(row) + b"\n" for row in result)
        digest = _create_only(outdir / "GOLD_SOURCE_STAGING_PRIVATE.jsonl", payload)
        output_safe.update({
            "source_context_file_sha256": hashlib.sha256(raw_source).hexdigest(),
            "previous_staged_file_sha256": hashlib.sha256(raw_prior).hexdigest(),
            "system_prompt_sha256": safe["system_prompt_sha256"],
            "staged_file_sha256": digest,
        })
        _create_only(
            outdir / "GOLD_SOURCE_STAGING_SAFE.json",
            json.dumps(output_safe, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n",
        )
    except BaseException:
        for file in outdir.iterdir():
            file.unlink()
        outdir.rmdir()
        raise
    return output_safe


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-context-jsonl", type=Path, required=True)
    p.add_argument("--previous-staged-jsonl", type=Path, required=True)
    p.add_argument("--previous-staging-safe", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    a = p.parse_args()
    try:
        receipt = run(a.source_context_jsonl, a.previous_staged_jsonl, a.previous_staging_safe, a.output_dir)
        print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - no untrusted/private errors in logs
        print(json.dumps({
            "schema": SCHEMA,
            "status": "CONTIGUOUS_SUFFIX_SOURCE_STAGE_HOLD",
            "quality_v1_admitted": 0,
            "training_authorized": False,
            "gpu_started": False,
            "private_values_emitted": False,
            "r50_accessed": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
