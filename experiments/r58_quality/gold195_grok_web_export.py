#!/usr/bin/env python3
"""Export first 3 private Gold195 tasks into 6 isolated Grok webpage review packets.

Offline only. Private files stay outside repo. No model result or approval is invented.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat

DIMENSIONS = ("chinese_prose", "character_consistency", "npc_initiative",
              "player_agency", "rule_fidelity", "narrative_continuity")
FLAGS = ("serious_player_agency", "hard_fact_or_ban", "safety_exclusion")
TASK_SCHEMA = "r58_gold195_six_dimension_review_task_private_v1"
MANIFEST_SCHEMA = "r58_gold195_grok_web_manifest_private_v1"
MAX_BYTES = 90 * 1024 * 1024


def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def private_read(path):
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ValueError("not a private absolute input")
    st = path.stat()
    if (not stat.S_ISREG(st.st_mode) or stat.S_IMODE(st.st_mode) != 0o600
            or st.st_nlink != 1 or not 0 < st.st_size <= MAX_BYTES):
        raise ValueError("private file permissions or size")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as file:
        opened = os.fstat(file.fileno())
        if (opened.st_ino, opened.st_dev) != (st.st_ino, st.st_dev):
            raise ValueError("source changed during read")
        raw = file.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("oversized private source")
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    if len(rows) != 63:
        raise ValueError("expected 63 frozen tasks")
    seen = set()
    for r in rows:
        if (not isinstance(r, dict) or r.get("schema") != TASK_SCHEMA
                or not isinstance(r.get("case_id"), str) or not r["case_id"]
                or r["case_id"] in seen
                or r.get("review_results") != []
                or r.get("review_status") != "UNREVIEWED"
                or r.get("input_design_status") != "PROPOSED_OFFLINE_CARD_NOT_APPROVED"
                or r.get("quality_v1_admitted") is not False
                or r.get("training_authorized") is not False
                or not isinstance(r.get("messages"), list)
                or not isinstance(r.get("target_text"), str)):
            raise ValueError("task contract")
        seen.add(r["case_id"])
        if sha(canon(r["messages"])) != r.get("input_messages_sha256"):
            raise ValueError("messages hash")
        if sha(r["target_text"].encode()) != r.get("target_sha256"):
            raise ValueError("target hash")
    return rows


def packet(row, label, reviewer):
    lines = [
        "# StoryForge R58 / Grok 4.7 独立中文剧情审核",
        "",
        "本地编号：" + label,
        "评审：" + reviewer + "（独立新对话；不得查看另一评审结果）",
        "",
        "任务：仅评价既有 Gold 回复，不续写、不修改；来源故事卡是拟议离线 System，",
        "不是经认证的历史生成请求或已批准的训练卡。根据可见材料评价，未知则指出未知。",
        "请按六维各给 1–5 的整数分、逐维理由，并判断严重侵犯玩家自主权、",
        "明确违反硬设定/禁令、内容安全排除。检查角色卡与历史及 Gold 的具体冲突。",
        "证据摘引必须逐字出自下方 Gold 回复，每段不超过 120 字。",
        "六维准入参考门槛：中文文笔4、人物一致4、NPC主动3、玩家自主4、硬规则4、连续性4。",
        "这不是自动训练准入。只返回有效 JSON，不要额外说明或 Markdown 包裹。",
        "",
        "## 拟议离线世界卡及历史",
    ]
    for i, message in enumerate(row["messages"]):
        lines += ["", "### 消息 " + str(i + 1) + " (" + message["role"] + ")",
                  "", message["content"]]
    lines += [
        "", "## 待审 Gold Assistant 目标（不要续写）", "", row["target_text"], "",
        "## 输出 JSON 格式", "",
        "下列 null 与空字符串仅代表占位；必须换成真实评分、理由和严重问题标志。",
        "card_design_verdict 只能为 ACCEPTABLE_FOR_OFFLINE_REVIEW、CONFLICT 或 UNCERTAIN。",
        "evidence_quotes 必须为 Gold 原文中的逐字短引用。",
        "",
        "~~~json",
        json.dumps({
            "scores": {k: None for k in DIMENSIONS},
            "severe_flags": {k: None for k in FLAGS},
            "reasons": {k: "" for k in DIMENSIONS},
            "card_design_verdict": "UNCERTAIN",
            "card_gold_conflicts": [],
            "evidence_quotes": [],
        }, ensure_ascii=False, indent=2),
        "~~~", "",
    ]
    return "\n".join(lines).encode("utf-8")


def create_files(rows):
    files = {}
    manifest = []
    for i, row in enumerate(rows[:3], 1):
        label = "case%02d" % i
        manifest.append({
            "label": label, "case_id": row["case_id"],
            "input_messages_sha256": row["input_messages_sha256"],
            "target_sha256": row["target_sha256"],
            "target_text": row["target_text"],
        })
        for reviewer in ("A", "B"):
            files[label + "-reviewer-" + reviewer + ".md"] = packet(row, label, reviewer)
    files["review-manifest.private.json"] = json.dumps({
        "schema": MANIFEST_SCHEMA, "cases": manifest,
        "quality_approved": False, "reviewer_results": [],
    }, ensure_ascii=False, indent=2).encode("utf-8")
    return files


def export(root, folder, rows):
    if not folder.is_absolute() or folder.is_symlink() or folder.exists():
        raise ValueError("output folder must be a new absolute path")
    parent = folder.parent
    if (not parent.is_dir() or parent.is_symlink()
            or stat.S_IMODE(parent.stat().st_mode) & 0o077
            or root.resolve() == parent.resolve()
            or root.resolve() in parent.resolve().parents):
        raise ValueError("output folder must be private outside Git")
    payload = create_files(rows)
    folder.mkdir(mode=0o700)
    for name, data in payload.items():
        fd = os.open(folder / name, os.O_CREAT | os.O_EXCL | os.O_WRONLY |
                     getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(data)
    return len(payload)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", type=Path, required=True)
    ap.add_argument("--private-tasks", type=Path, required=True)
    ap.add_argument("--private-output-dir", type=Path)
    a = ap.parse_args()
    try:
        rows = private_read(a.private_tasks)
        written = export(a.repo_root, a.private_output_dir, rows) if a.private_output_dir else 0
        result = {
            "schema": "r58_gold195_grok_web_export_safe_v1",
            "status": ("WEB_PILOT_PACKETS_EXPORTED__UNREVIEWED" if written
                       else "WEB_PILOT_DRY_RUN_VALID"),
            "source_tasks_verified": len(rows),
            "pilot_cases": 3, "reviewer_packets": 6,
            "private_files_created": written,
            "reviews_completed": 0, "quality_v1_admitted": 0,
            "network_called": False, "r50_accessed": False,
        }
    except Exception:
        result = {
            "schema": "r58_gold195_grok_web_export_safe_v1",
            "status": "SOURCE_OR_OUTPUT_UNAVAILABLE__HOLD",
            "quality_v1_admitted": 0, "network_called": False,
        }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"].startswith(("WEB_PILOT_PACKETS_EXPORTED", "WEB_PILOT_DRY_RUN")) else 42


if __name__ == "__main__":
    raise SystemExit(main())
