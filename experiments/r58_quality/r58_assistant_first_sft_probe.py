#!/usr/bin/env python3
"""R58 Assistant-first SFT engineering probe, NOT a training-data release.

Convert the frozen PRIVATE semantic-review132 source into exact assistant-first
chat rows for actual ms-swift template/collator checks. The source card is NOT
admitted or inserted. Never put the output in Git; never read R50.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

SOURCE_SCHEMA = "r58_hf_semantic_review_input_private_v1"
PROBE_SCHEMA = "r58_gold195_sft_assistant_first_probe_private_v1"
SYSTEM = (
    "你是中文互动剧情的叙事助手。尊重玩家角色的选择与自主权，"
    "保持已有角色关系、剧情时间线和世界规则一致。"
    "不得擅自替玩家决定重要行动。"
)
MAX_BYTES = 120 * 1024 * 1024


def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def read_source(path: Path):
    if (not path.is_absolute() or path.is_symlink() or not path.is_file()
            or not 0 < path.stat().st_size <= MAX_BYTES):
        raise ValueError("private source path invalid")
    rows = [json.loads(line) for line in path.read_bytes().splitlines() if line.strip()]
    if len(rows) != 132:
        raise ValueError("exact 132 source rows required")
    return rows


def convert(rows):
    if len(rows) != 132:
        raise ValueError("exact 132 source rows required")
    result = []
    digest_seen = set()
    first_roles = 0
    for i, row in enumerate(rows, 1):
        if (not isinstance(row, dict)
                or row.get("schema") != SOURCE_SCHEMA
                or row.get("review_label") != f"full{i:03d}"
                or row.get("training_authorized") is not False):
            raise ValueError("source contract not satisfied")
        history = row.get("original_history")
        current = row.get("current_user_text")
        target = row.get("frozen_target_text")
        if (not isinstance(history, list) or not history
                or not isinstance(current, str) or not current.strip()
                or not isinstance(target, str) or not target.strip()):
            raise ValueError("empty or missing chat input")
        if history[0].get("role") != "assistant":
            raise ValueError("expected leading assistant; do not repair history")
        first_roles += 1
        clean_history = []
        for msg in history:
            if (not isinstance(msg, dict) or msg.get("role") not in ("user", "assistant")
                    or not isinstance(msg.get("content"), str) or not msg["content"]):
                raise ValueError("unsupported history message")
            clean_history.append({"role": msg["role"], "content": msg["content"],
                                  "loss": False})
        # Conversation is preserved byte-for-byte in content and order, not
        # auto-repaired to enforce role alternation or a user-first template.
        if hashlib.sha256(canon(history)).hexdigest() != row.get("original_history_sha256"):
            raise ValueError("original history hash mismatch")
        if hashlib.sha256(target.encode("utf-8")).hexdigest() != row.get("source_target_sha256"):
            raise ValueError("frozen target hash mismatch")
        digest = row["source_target_sha256"]
        if digest in digest_seen:
            raise ValueError("duplicate frozen target digest")
        digest_seen.add(digest)
        messages = ([{"role": "system", "content": SYSTEM, "loss": False}]
                    + clean_history
                    + [{"role": "user", "content": current, "loss": False},
                       {"role": "assistant", "content": target, "loss": True}])
        result.append({"messages": messages})
    assert first_roles == 132
    return result


def prepare(source: Path, output: Path, repo: Path):
    if (not output.is_absolute() or output.exists() or output.is_symlink()
            or repo.resolve() == output.resolve()
            or repo.resolve() in output.resolve().parents
            or not output.parent.is_dir()
            or stat.S_IMODE(output.parent.stat().st_mode) & 0o077):
        raise ValueError("private output path invalid")
    rows = read_source(source)
    probes = convert(rows)
    data = b"".join(canon(row) + b"\n" for row in probes)
    fd = os.open(output, os.O_CREAT | os.O_EXCL | os.O_WRONLY
                 | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
    return {
        "schema": PROBE_SCHEMA,
        "status": "R58_ASSISTANT_FIRST_SFT_PROBE_PREPARED__NOT_ADMITTED",
        "rows": len(probes),
        "assistant_first_preserved": len(probes),
        "output_sha256": hashlib.sha256(data).hexdigest(),
        "source_cards_included": False,
        "gold_content_transformed": False,
        "history_truncation_approved": False,
        "training_authorized": False,
        "quality_v1_admitted": 0,
        "r50_accessed": False,
        "private_text_emitted": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-input", required=True, type=Path)
    parser.add_argument("--private-output", required=True, type=Path)
    parser.add_argument("--repo-root", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = prepare(args.private_input, args.private_output, args.repo_root)
        code = 0
    except Exception:
        report = {"schema": PROBE_SCHEMA,
                  "status": "R58_ASSISTANT_FIRST_SFT_PROBE_HOLD",
                  "training_authorized": False, "quality_v1_admitted": 0,
                  "r50_accessed": False, "private_text_emitted": False}
        code = 42
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
