"""Build Gold-free, context-enriched Chinese blind scoring sheets.

Match by SHA256 of the exact inference prompt, not dataset row position.
Never read answer key or Gold responses.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.analyze_blind_eval import CHINESE_SCORE_FIELDS


def prompt_digest(messages: list[dict]) -> str:
    payload = json.dumps({"messages": messages}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def format_messages(messages: list[dict]) -> str:
    roles = {"system": "系统规则/故事背景", "user": "用户", "assistant": "历史助手"}
    return "\n\n".join(
        f"【{roles.get(m['role'], m['role'])}】\n{m['content']}"
        for m in messages
    )


def export_context_review(
    prompts_path: Path, manifest_path: Path, pairs_path: Path, out_dir: Path
) -> int:
    prompts = read_jsonl(prompts_path)
    pairs = read_jsonl(pairs_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest["samples"]
    if manifest.get("schema") != "storyforge-blind-v1":
        raise ValueError("unexpected manifest schema")
    if not (len(prompts) == len(pairs) == len(entries) == manifest["count"]):
        raise ValueError("prompt, manifest and blind pair counts do not match")
    if len(prompts) not in (15, 20):
        raise ValueError("expected 15 validation or 20 held-out samples")
    lookup = {}
    for prompt, entry in zip(prompts, entries):
        messages = prompt["messages"]
        digest = prompt_digest(messages)
        if digest != entry["prompt_sha256"]:
            raise ValueError("source prompt hash mismatch")
        if not messages or messages[-1]["role"] != "user":
            raise ValueError("last source message must be user")
        if any("loss" in m for m in messages):
            raise ValueError("loss metadata found in evaluation prompt")
        if entry["sample_id"] in lookup:
            raise ValueError("duplicate manifest sample ID")
        lookup[entry["sample_id"]] = (messages, digest)

    expected_ids = set(lookup)
    if {row["sample_id"] for row in pairs} != expected_ids:
        raise ValueError("blind pairs do not match prompt manifest")
    if len({row["sample_id"] for row in pairs}) != len(pairs):
        raise ValueError("duplicate blind pair")

    headers = ["样本编号", "故事背景与系统规则", "历史对话", "当前用户输入",
               "回复A", "回复B", "整体偏好(A/B/TIE)", "评分理由", "严重问题"]
    headers += [f"{label}·{arm}" for label in CHINESE_SCORE_FIELDS.values()
                for arm in ("A", "B")]
    data = []
    for pair in pairs:
        messages, digest = lookup[pair["sample_id"]]
        if digest != pair["prompt_sha256"]:
            raise ValueError(f"pair hash mismatch: {pair['sample_id']}")
        if not all(isinstance(m.get("content"), str) for m in messages):
            raise ValueError("non-text message content requires separate review")
        responses = (pair["response_a"], pair["response_b"])
        if not all(isinstance(x, str) and x.strip() for x in responses):
            raise ValueError("empty model response")
        data.append({
            "样本编号": pair["sample_id"],
            "故事背景与系统规则": format_messages(
                [m for m in messages if m["role"] in ("system", "developer")]
            ),
            "历史对话": format_messages(
                [m for m in messages[:-1] if m["role"] not in ("system", "developer")]
            ),
            "当前用户输入": messages[-1]["content"],
            "回复A": responses[0],
            "回复B": responses[1],
        })

    out_dir.mkdir(parents=True, exist_ok=True)
    destinations = [out_dir / f"StoryForge_Reviewer_{i:02d}.csv" for i in range(1, 4)]
    if any(path.exists() for path in destinations):
        raise FileExistsError("refusing to overwrite reviewer sheets")
    for path in destinations:
        with path.open("x", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=headers)
            writer.writeheader()
            writer.writerows(data)
    return len(data)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompts", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--pairs", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    print(f"CONTEXT_BLIND_REVIEW_PASS: {export_context_review(args.prompts, args.manifest, args.pairs, args.out_dir)}")


if __name__ == "__main__":
    main()
