#!/usr/bin/env python3
"""Create three targeted PRIVATE Grok web follow-up packets for R58 pilot.

Case02: independent arbitration of severe flag vs provisional pass.
Case03: separate A/B retry materials without exposing original review output.
Original six reviews and Gold are never modified; no network or training.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat

from gold195_grok_web_triage import triage
from gold195_grok_web_validate import read_private_json

MAX_PACKET_BYTES = 25 * 1024 * 1024


def source_markdown(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("missing source review Markdown")
    st = path.stat()
    if (not stat.S_ISREG(st.st_mode) or stat.S_IMODE(st.st_mode) != 0o600
            or st.st_nlink != 1 or not 0 < st.st_size <= MAX_PACKET_BYTES):
        raise ValueError("private markdown security/size")
    return path.read_text(encoding="utf-8")


def make_packets(folder):
    report = triage(folder)
    cases = report["cases"]
    if (len(cases) != 3
            or cases[1]["reviewer_A"]["state"] != "SEVERE_FLAG"
            or cases[1]["reviewer_B"]["state"] != "PROVISIONAL_REVIEW_PASS"
            or cases[2]["reviewer_A"]["state"] != "MALFORMED"
            or cases[2]["reviewer_B"]["state"] != "EVIDENCE_QUOTE_NOT_IN_GOLD"):
        raise ValueError("pilot differs from expected triage; manual review required")
    a = read_private_json(folder / "case02-reviewer-A.json")
    b = read_private_json(folder / "case02-reviewer-B.json")
    # First independent A/B reviews have concluded; arbitration may now read both.
    original = source_markdown(folder / "case02-reviewer-A.md")
    arbiter = "\n".join([
        "# R58 Case02 — 独立严重问题仲裁（不续写故事）",
        "",
        "这是第三次仲裁，允许看到前两次已完成审核的结论，不能仅因多数意见撤销严重标记。",
        "只核查 A 标注的严重问题与其在世界卡/历史/Gold 中的直接依据。",
        "若属于玩家自主权侵犯、明确硬规则违反或安全排除，判断证据是否足够；",
        "若仅是风格偏好、未出现的世界事实或普通 NPC 自主行动，不自动认定严重违规。",
        "请提供引用 Gold 的逐字短证据、引用的故事规则依据与明确的独立理由。",
        "若无法判断，保持 UNCERTAIN/HOLD。不得修改原始 Gold，不得自动授予训练 PASS。",
        "",
        "## 原始审题（仅 Case02）", original,
        "",
        "## Reviewer A 的原始 JSON（严重标志）",
        json.dumps(a, ensure_ascii=False, indent=2),
        "",
        "## Reviewer B 的原始 JSON（暂定通过）",
        json.dumps(b, ensure_ascii=False, indent=2),
        "",
        "## 仲裁返回 JSON",
        "请返回下列全部字段，结论仅限 CONFIRMED_SEVERE、NOT_SUPPORTED 或 UNCERTAIN：",
        json.dumps({
            "arbiter_verdict": "UNCERTAIN",
            "severe_flag_names": [],
            "gold_exact_quotes": [],
            "rule_or_card_evidence": [],
            "analysis": "",
            "remaining_uncertainty": "",
        }, ensure_ascii=False, indent=2),
        "",
    ])
    retry_intro = "\n".join([
        "# Case03 独立重审",
        "",
        "请在**全新聊天**审阅同一 Gold。上次输出存在技术格式/引文问题，",
        "本次不要依据任何先前评价；以下仍是唯一审题材料。",
        "请完整输出一个 JSON 对象，六维整数 1~5，严重标志为 JSON true/false，",
        "理由不得留空。引用必须逐字摘自 Gold Assistant 目标，而不是 System 或历史对话。",
        "没有足够依据则将卡片结论标记 UNCERTAIN，禁止编造引用或默认评分通过。",
        "",
    ])
    return {
        "case02-independent-severe-arbitration.md": arbiter.encode("utf-8"),
        "case03-reviewer-A-retry.md": (
            retry_intro + source_markdown(folder / "case03-reviewer-A.md")).encode("utf-8"),
        "case03-reviewer-B-retry.md": (
            retry_intro + source_markdown(folder / "case03-reviewer-B.md")).encode("utf-8"),
    }


def safe_output(folder, repo_root):
    if not folder.is_absolute() or folder.exists() or folder.is_symlink():
        raise ValueError("output must be a new private absolute directory")
    parent = folder.parent
    if (not parent.is_dir() or parent.is_symlink()
            or stat.S_IMODE(parent.stat().st_mode) & 0o077
            or repo_root.resolve() == parent.resolve()
            or repo_root.resolve() in parent.resolve().parents):
        raise ValueError("private directory must remain outside Git")
    folder.mkdir(mode=0o700)


def write_packets(packets, folder, root):
    safe_output(folder, root)
    for name, body in packets.items():
        fd = os.open(folder / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                     getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(body)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", type=Path, required=True)
    p.add_argument("--private-pilot-dir", type=Path, required=True)
    p.add_argument("--private-followup-dir", type=Path)
    args = p.parse_args()
    try:
        packets = make_packets(args.private_pilot_dir)
        if args.private_followup_dir:
            write_packets(packets, args.private_followup_dir, args.repo_root)
        result = {
            "schema": "r58_gold195_grok_web_targeted_followup_safe_v1",
            "status": ("FOLLOWUP_PACKETS_EXPORTED__NO_NEW_REVIEWS"
                       if args.private_followup_dir else "FOLLOWUP_DRY_RUN_VALID"),
            "followup_review_packets": len(packets),
            "distinct_original_gold_cases": 2,
            "original_six_reviews_untouched": True,
            "private_files_written": len(packets) if args.private_followup_dir else 0,
            "quality_v1_admitted": 0, "r50_accessed": False,
            "network_called": False, "gpu_authorized": False,
        }
        exit_code = 0
    except Exception:
        result = {
            "schema": "r58_gold195_grok_web_targeted_followup_safe_v1",
            "status": "PILOT_REVIEW_OR_PRIVATE_OUTPUT_MISMATCH__HOLD",
            "quality_v1_admitted": 0, "network_called": False,
        }
        exit_code = 42
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
