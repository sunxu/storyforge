"""R60 exact cross-case target-in-history dependencies, CPU-only.

Reuse R59 SFT preview validation. This detects only literal containment, not
semantic leakage, historical train exposure or independent world components.
No automatic split, admission, freeze, model, DB or R50 access.
"""
from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from collections import Counter
from pathlib import Path

from quality_v1 import canonical, sha
from r59_sft_collator_cpu import validate_preview_row
from r60_p3_stage_pair_probe import ALLOWED_BASE, Hold, parse_lines, private_bytes

SCHEMA = "storyforge_r60_experimental_cross_case_dependency_safe_v1"
REVIEW_SCHEMA = "storyforge_r60_e03_ai_semantic_result_private_v1"
NOT_ACTUAL_SENT = "RECONSTRUCTED_NOT_ACTUAL_SENT"


def analyze(previews: list[dict], reviews: list[dict]):
    if len(previews) != 3 or len(reviews) != 3:
        raise Hold("THREE_CASES_REQUIRED")
    nodes, seen, targets = [], set(), set()
    for row, review in zip(previews, reviews, strict=True):
        validate_preview_row(row)
        if not isinstance(review, dict) or review.get("schema") != REVIEW_SCHEMA:
            raise Hold("REVIEW_SCHEMA_INVALID")
        cid = review.get("case_id")
        digest = row["metadata"]["source_target_sha256"]
        messages = row["messages"]
        input_hash = sha(canonical([
            {"role": m["role"], "content": m["content"]}
            for m in messages[:-1]
        ]))
        if (not isinstance(cid, str) or not cid or cid in seen
                or digest in targets
                or review.get("source_target_sha256") != digest
                or review.get("input_messages_sha256") != input_hash
                or review.get("decision") != "PASS"
                or review.get("context_provenance") != NOT_ACTUAL_SENT
                or review.get("owner_attestation") is not False
                or review.get("quality_v1_admitted") is not False
                or review.get("training_authorized") is not False):
            raise Hold("REVIEW_IDENTITY_OR_STATE_INVALID")
        seen.add(cid)
        targets.add(digest)
        nodes.append({
            "case_id": cid,
            "target_sha256": digest,
            "target": messages[-1]["content"],
            "history": messages[1:-1],
        })

    edges = []
    parent = list(range(3))

    def find(i):
        while parent[i] != i:
            i = parent[i]
        return i

    def join(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for i, src in enumerate(nodes):
        for j, dst in enumerate(nodes):
            if i == j:
                continue
            for k, msg in enumerate(dst["history"]):
                content = msg["content"]
                target = src["target"]
                if msg["role"] != "assistant" or target not in content:
                    continue
                kind = "EXACT_MESSAGE" if target == content else "CONTAINED_SUBSTRING"
                edges.append({
                    "from_case_id": src["case_id"],
                    "to_case_id": dst["case_id"],
                    "history_index": k,
                    "match_kind": kind,
                    "split_across_this_edge_forbidden": True,
                })
                join(i, j)
    components = {}
    for i, node in enumerate(nodes):
        components.setdefault(find(i), []).append(node["case_id"])
    groups = sorted((sorted(ids) for ids in components.values()), key=lambda x: x[0])
    counts = Counter(e["match_kind"] for e in edges)
    private = {
        "schema": "storyforge_r60_experimental_dependency_private_v1",
        "status": "EXACT_TEXT_DEPENDENCY_ONLY_NOT_WORLD_GRAPH",
        "nodes": [{
            "case_id": n["case_id"], "target_sha256": n["target_sha256"],
        } for n in nodes],
        "edges": edges,
        "literal_connected_components": groups,
        "world_components_verified": False,
        "historical_exposure_verified": False,
        "split_approved": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
    }
    safe = {
        "schema": SCHEMA,
        "status": "CROSS_CASE_LITERAL_DEPENDENCY_CHECKED__WORLD_SPLIT_HOLD",
        "cases_checked": 3,
        "semantic_reviews_matched": 3,
        "literal_dependency_edges": len(edges),
        "exact_assistant_message_edges": counts["EXACT_MESSAGE"],
        "contained_assistant_message_edges": counts["CONTAINED_SUBSTRING"],
        "literal_connected_components": len(groups),
        "largest_literal_component": max(map(len, groups)),
        "all_three_connected_by_literal_edges": len(groups) == 1,
        "cross_split_on_detected_edges_allowed": False,
        "world_component_independently_verified": False,
        "protected_set_completeness_verified": False,
        "historical_train_validation_test_exposure_verified": False,
        "train_validation_split_frozen": False,
        "e0_e3_owner_verified": 0,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "database_modified": False,
        "r50_accessed": False,
        "private_values_emitted": False,
    }
    return private, safe


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--experimental-preview", type=Path, required=True)
    p.add_argument("--validated-ai-results", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()
    try:
        previews = parse_lines(private_bytes(args.experimental_preview, 30_000_000), 3)
        reviews = parse_lines(private_bytes(args.validated_ai_results, 8_000_000), 3)
        output = args.output_dir
        if (not output.is_absolute() or output.is_symlink() or output.exists()
                or not output.is_relative_to(ALLOWED_BASE / "r59/private")
                or not output.parent.is_dir() or output.parent.is_symlink()
                or stat.S_IMODE(output.parent.stat().st_mode) != 0o700):
            raise Hold("PRIVATE_OUTPUT_INVALID")
        private, safe = analyze(previews, reviews)
        output.mkdir(mode=0o700)
        try:
            for name, value in (
                ("R60_CROSS_CASE_DEPENDENCY_PRIVATE.json", private),
                ("R60_CROSS_CASE_DEPENDENCY_SAFE.json", safe),
            ):
                fd = os.open(output / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                             | getattr(os, "O_NOFOLLOW", 0), 0o600)
                with os.fdopen(fd, "wb") as handle:
                    handle.write(canonical(value) + b"\n")
                    handle.flush()
                    os.fsync(handle.fileno())
        except BaseException:
            for child in output.iterdir():
                child.unlink()
            output.rmdir()
            raise
        print(json.dumps(safe, ensure_ascii=False, sort_keys=True))
        return 0
    except (Hold, OSError, ValueError, TypeError, KeyError, UnicodeError):
        print(json.dumps({
            "schema": SCHEMA,
            "status": "CROSS_CASE_DEPENDENCY_INPUT_HOLD",
            "quality_v1_admitted": 0,
            "training_authorized": False,
            "gpu_started": False,
            "database_modified": False,
            "r50_accessed": False,
            "private_values_emitted": False,
        }, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
