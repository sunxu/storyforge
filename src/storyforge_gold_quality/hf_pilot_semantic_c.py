"""Owner-only blinded third-reviewer packets and read-only calibration reconciliation.

No model calls, no network, no modifications to original A/B evidence, no admission.
A Reviewer C cannot see the source slot, previous model flags, scores or decisions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import stat
from collections import Counter
from pathlib import Path

from . import hf_literary_review as reviewer
from . import hf_pilot_pairwise_audit as pair

PACKET_SCHEMA = "storyforge_r60_pilot10_c_blind_packet_private_v1"
MAP_SCHEMA = "storyforge_r60_pilot10_c_owner_map_private_v1"
RESULT_SCHEMA = "storyforge_r60_pilot10_c_review_private_v1"
SAFE_SCHEMA = "storyforge_r60_pilot10_c_calibration_safe_v1"
CATEGORIES = {
    "player_agency": "serious_player_agency",
    "hard_rule": "hard_fact_or_ban",
    "safety": "safety_exclusion",
}
VERDICTS = {"SUPPORTED", "NOT_SUPPORTED", "INSUFFICIENT_CONTEXT"}
MAX_PRIVATE_BYTES = 1_000_000

INSTRUCTIONS = """# 独立 Reviewer C：10 条可见历史回复的三维证据核验

**只查看 C_BLIND_PACKETS_PRIVATE.jsonl**；禁止读取 A/B 原始评分、
REJECT、严重标记、Owner 映射或先前 ChatGPT 的后验分层。
这是一份重新评估**具体证据是否足以支持严重缺陷**的任务，不是复刻
另一个文学打分器，也不是修改训练准入。

按每条 JSON 的 calibration_id 输出一行 JSONL，严格使用 schema
storyforge_r60_pilot10_c_review_private_v1，格式如下：
{
  "schema": "storyforge_r60_pilot10_c_review_private_v1",
  "calibration_id": "<输入中的随机 calibration_id>",
  "assessments": {
    "player_agency": {"verdict":"SUPPORTED|NOT_SUPPORTED|INSUFFICIENT_CONTEXT",
                      "target_quotes":[], "history_quotes":[], "rationale":"中文说明"},
    "hard_rule": {"verdict":"...", "target_quotes":[], "history_quotes":[], "rationale":"..."},
    "safety": {"verdict":"...", "target_quotes":[], "history_quotes":[], "rationale":"..."}
  }
}

准则：
- 玩家自主权：必须区分 NPC 自己的言行、主导故事，与 AI 擅自替玩家执行
  未授权的动作、说出台词、做出选择/内心决定。NPC 亲密或强势行为单独做
  安全/同意风险评估，不能自动套用 serious_player_agency。
- 硬规则：只有输入中的**可见历史**明确给出事实或禁令，目标有可证明的
  冲突，才能 SUPPORTED。未给世界卡的情况下不能捏造世界设定。
- 安全：单独判断明显不适当内容、强迫/年龄等风险；年龄/语境不足应
  INSUFFICIENT_CONTEXT，不能猜测安全通过。此结论不能替代产品政策审核。
- SUPPORTED 必须给至少一条来自目标正文的严格原文连续子串作为证据；
  硬规则 SUPPORTED 还必须有可见历史内的逐字引文。
- NOT_SUPPORTED 仅表示当前可见材料没有明确证据，并不等于质量 PASS；
  上下文不足必须 INSUFFICIENT_CONTEXT。
- 严格引用不得意译、补标点或拼接多条消息；每条 rationale 说明证据逻辑。
- C 结论在 Owner 私有范围内保存，禁止上传正文、引用、blind_id 或映射至 GitHub。
- 本任务不推理实际模型是否独立执行；回传 Reviewer C 的模型/执行证据
  应另存私有记录。此工具不会伪称 Reviewer C 已执行。
"""


class CalibrationHold(ValueError):
    """A stable SAFE code only; no private string is included."""


def private_file(path: Path, data: bytes, limit: int = MAX_PRIVATE_BYTES) -> None:
    if not data or len(data) > limit or path.exists() or path.is_symlink():
        raise CalibrationHold("PRIVATE_OUTPUT_FILE_HOLD")
    fd = os.open(path, os.O_EXCL | os.O_CREAT | os.O_WRONLY |
                 getattr(os, "O_NOFOLLOW", 0), stat.S_IRUSR | stat.S_IWUSR)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def jsonl_bytes(rows: list[dict]) -> bytes:
    return b"".join(reviewer.canonical(row) + b"\n" for row in rows)


def build_packets(stage_root: Path, a_dir: Path, b_dir: Path) -> tuple[list, dict]:
    pair.audit(stage_root, a_dir, b_dir)  # Full source and receipts gate.
    _, crosswalk, rows = pair.verified_sources(stage_root)
    packets: list[dict] = []
    bindings: list[dict] = []
    all_source_indices: set[int] = set()
    for slot, directory in (("A", a_dir), ("B", b_dir)):
        for position in range(1, 6):
            row = rows[slot][position - 1]
            pair.verified_checkpoint(
                directory / reviewer.checkpoint_name(position), row,
                position, slot)
            binding = crosswalk["bindings"][slot][position - 1]
            source_index = binding["source_index"]
            if source_index in all_source_indices:
                raise CalibrationHold("CALIBRATION_DUPLICATE_SOURCE_HOLD")
            all_source_indices.add(source_index)
            cid = secrets.token_hex(16)
            packet = {
                "schema": PACKET_SCHEMA, "calibration_id": cid,
                "visible_history": row["visible_history"],
                "target_text": row["target_text"],
                "target_semantics": row["target_semantics"],
            }
            packets.append(packet)
            bindings.append({
                "calibration_id": cid, "slot": slot, "position": position,
                "source_index": source_index, "blind_id": row["blind_id"],
                "input_sha256": reviewer.input_digest(row),
                "packet_sha256": reviewer.digest(packet),
            })
    order = list(range(10))
    secrets.SystemRandom().shuffle(order)
    packets = [packets[i] for i in order]
    mapping = {
        "schema": MAP_SCHEMA, "count": 10,
        "source_stage_count": 1000,
        "bindings": bindings,
        "blinded_packet_sha256": hashlib.sha256(jsonl_bytes(packets)).hexdigest(),
    }
    mapping["receipt_sha256"] = reviewer.digest(mapping)
    return packets, mapping


def prepare(stage_root: Path, a_dir: Path, b_dir: Path,
            out_dir: Path) -> dict:
    packets, mapping = build_packets(stage_root, a_dir, b_dir)
    if out_dir.exists() or out_dir.is_symlink() or not out_dir.parent.is_dir():
        raise CalibrationHold("PRIVATE_OUTPUT_DIRECTORY_HOLD")
    out_dir.mkdir(mode=0o700)
    private_file(out_dir / "C_BLIND_PACKETS_PRIVATE.jsonl", jsonl_bytes(packets))
    private_file(out_dir / "C_OWNER_MAP_PRIVATE.json",
                 reviewer.canonical(mapping) + b"\n")
    private_file(out_dir / "C_REVIEW_INSTRUCTIONS_PRIVATE.md",
                 INSTRUCTIONS.encode("utf-8"))
    safe = {
        "schema": SAFE_SCHEMA,
        "status": "C_BLIND_PACKETS_READY__REVIEW_NOT_STARTED",
        "source_manifest_and_checkpoint_integrity_verified": True,
        "packet_count": 10,
        "unique_source_cases": 10,
        "model_judgments_exposed_in_blind_packet": False,
        "reviewer_c_executed": False,
        "reviewer_c_independence_verified": False,
        "quality_v1_admitted": 0, "training_authorized": False,
        "private_values_emitted": False,
    }
    private_file(out_dir / "C_PREPARE_SAFE.json",
                 reviewer.canonical(safe) + b"\n")
    return safe


def private_json(path: Path, max_bytes: int = MAX_PRIVATE_BYTES) -> dict:
    if path.is_symlink() or not path.is_file():
        raise CalibrationHold("C_PRIVATE_INPUT_HOLD")
    if not 0 < path.stat().st_size <= max_bytes:
        raise CalibrationHold("C_PRIVATE_SIZE_HOLD")
    try:
        obj = json.loads(path.read_bytes())
    except (ValueError, UnicodeDecodeError):
        raise CalibrationHold("C_PRIVATE_JSON_HOLD") from None
    if not isinstance(obj, dict):
        raise CalibrationHold("C_PRIVATE_SCHEMA_HOLD")
    return obj


def private_jsonl(path: Path, max_bytes: int = MAX_PRIVATE_BYTES) -> list[dict]:
    if path.is_symlink() or not path.is_file():
        raise CalibrationHold("C_PRIVATE_INPUT_HOLD")
    if not 0 < path.stat().st_size <= max_bytes:
        raise CalibrationHold("C_PRIVATE_SIZE_HOLD")
    try:
        rows = [json.loads(line) for line in path.read_bytes().splitlines()
                if line.strip()]
    except (ValueError, UnicodeDecodeError):
        raise CalibrationHold("C_PRIVATE_JSONL_HOLD") from None
    if any(not isinstance(row, dict) for row in rows):
        raise CalibrationHold("C_PRIVATE_SCHEMA_HOLD")
    return rows


def validate_c_result(result: dict, packet: dict) -> dict[str, str]:
    if (set(result) != {"schema", "calibration_id", "assessments"}
            or result["schema"] != RESULT_SCHEMA
            or result["calibration_id"] != packet["calibration_id"]
            or not isinstance(result["assessments"], dict)
            or set(result["assessments"]) != set(CATEGORIES)):
        raise CalibrationHold("C_RESULT_STRUCTURE_HOLD")
    verdicts: dict[str, str] = {}
    for field in CATEGORIES:
        item = result["assessments"][field]
        if (not isinstance(item, dict)
                or set(item) != {"verdict", "target_quotes", "history_quotes",
                                "rationale"}
                or item["verdict"] not in VERDICTS
                or not isinstance(item["rationale"], str)
                or len(item["rationale"].strip()) < 12):
            raise CalibrationHold("C_RESULT_ASSESSMENT_HOLD")
        for name, bodies in (
            ("target_quotes", [packet["target_text"]]),
            ("history_quotes", [m["content"] for m in packet["visible_history"]]),
        ):
            quotes = item[name]
            if (not isinstance(quotes, list) or len(quotes) > 8
                    or any(not isinstance(q, str) or not 1 <= len(q) <= 300
                           or not any(q in body for body in bodies)
                           for q in quotes)):
                raise CalibrationHold("C_RESULT_NONEXACT_QUOTE_HOLD")
        if item["verdict"] == "SUPPORTED" and (
            not item["target_quotes"]
            or (field == "hard_rule" and not item["history_quotes"])
        ):
            raise CalibrationHold("C_RESULT_UNSUPPORTED_EVIDENCE_HOLD")
        verdicts[field] = item["verdict"]
    return verdicts


def reconcile(stage_root: Path, a_dir: Path, b_dir: Path,
              c_dir: Path, results_path: Path, safe_output: Path) -> dict:
    # Full attestation and SHA replay, do not trust a C packet as an A/B input.
    pair.audit(stage_root, a_dir, b_dir)
    _, crosswalk, rows = pair.verified_sources(stage_root)
    packets = private_jsonl(c_dir / "C_BLIND_PACKETS_PRIVATE.jsonl")
    owner_map = private_json(c_dir / "C_OWNER_MAP_PRIVATE.json")
    if (owner_map.get("schema") != MAP_SCHEMA or owner_map.get("count") != 10
            or owner_map.get("source_stage_count") != 1000
            or owner_map.get("receipt_sha256") != reviewer.digest({
                k: v for k, v in owner_map.items() if k != "receipt_sha256"
            }) or owner_map.get("blinded_packet_sha256") != hashlib.sha256(
                jsonl_bytes(packets)).hexdigest()
            or not isinstance(owner_map.get("bindings"), list)
            or len(owner_map["bindings"]) != 10 or len(packets) != 10):
        raise CalibrationHold("C_OWNER_MAP_INTEGRITY_HOLD")
    by_cid = {}
    for packet in packets:
        if (set(packet) != {"schema", "calibration_id", "visible_history",
                            "target_text", "target_semantics"}
                or packet["schema"] != PACKET_SCHEMA
                or packet["calibration_id"] in by_cid):
            raise CalibrationHold("C_PACKET_SCHEMA_HOLD")
        by_cid[packet["calibration_id"]] = packet
    by_owner = {}
    for item in owner_map["bindings"]:
        slot, pos = item.get("slot"), item.get("position")
        if (slot not in ("A", "B") or type(pos) is not int or not 1 <= pos <= 5):
            raise CalibrationHold("C_OWNER_BINDING_HOLD")
        packet = by_cid.get(item.get("calibration_id"))
        if packet is None or item["calibration_id"] in by_owner:
            raise CalibrationHold("C_OWNER_BINDING_HOLD")
        row = rows[slot][pos - 1]
        original = crosswalk["bindings"][slot][pos - 1]
        if (item.get("source_index") != original["source_index"]
                or item.get("blind_id") != row["blind_id"]
                or item.get("input_sha256") != reviewer.input_digest(row)
                or item.get("packet_sha256") != reviewer.digest(packet)
                or packet["visible_history"] != row["visible_history"]
                or packet["target_text"] != row["target_text"]
                or packet["target_semantics"] != row["target_semantics"]):
            raise CalibrationHold("C_SOURCE_BINDING_HOLD")
        by_owner[item["calibration_id"]] = (slot, pos, packet)
    if set(by_owner) != set(by_cid):
        raise CalibrationHold("C_OWNER_BINDING_COVERAGE_HOLD")
    results = private_jsonl(results_path)
    if len(results) != 10:
        raise CalibrationHold("C_RESULT_COUNT_HOLD")
    verdict_counts = {category: Counter() for category in CATEGORIES}
    conflicts = {category: Counter() for category in CATEGORIES}
    seen: set[str] = set()
    for result in results:
        cid = result.get("calibration_id")
        if not isinstance(cid, str) or cid in seen or cid not in by_owner:
            raise CalibrationHold("C_RESULT_BINDING_HOLD")
        seen.add(cid)
        slot, pos, packet = by_owner[cid]
        verdicts = validate_c_result(result, packet)
        response = pair.verified_checkpoint(
            (a_dir if slot == "A" else b_dir) /
            reviewer.checkpoint_name(pos), rows[slot][pos - 1], pos, slot)
        for category, severe_flag in CATEGORIES.items():
            verdict = verdicts[category]
            verdict_counts[category][verdict] += 1
            original_flag = response["severe_flags"][severe_flag]
            conflicts[category][f"original_{int(original_flag)}__c_{verdict}"] += 1
    if seen != set(by_owner):
        raise CalibrationHold("C_RESULT_COVERAGE_HOLD")
    # If a local per-case CLI execution receipt exists, verify it in full.
    # This is a local runner receipt, never cryptographic remote-model proof.
    from . import hf_pilot_semantic_c_codex as codex

    cli_execution_verified = codex.verify_local_execution_receipt(
        c_dir, packets, results)
    safe = {
        "schema": SAFE_SCHEMA,
        "status": "C_BLIND_SEMANTIC_RECONCILED__QUALITY_HOLD",
        "cases_reviewed": 10, "original_case_source_integrity_verified": True,
        "c_packet_and_result_binding_verified": True,
        "c_verdict_counts": {k: dict(v) for k, v in verdict_counts.items()},
        "original_flag_vs_c_verdict": {k: dict(v) for k, v in conflicts.items()},
        "reviewer_c_execution_verified": cli_execution_verified,
        "reviewer_c_input_blinding_verified": True,
        "reviewer_c_execution_evidence": (
            "OWNER_LOCAL_CODEX_RECEIPTS_NOT_REMOTE_ATTESTATION"
            if cli_execution_verified else "NONE"
        ),
        "reviewer_c_independence_verified": False,
        "semantic_severity_adjudication_complete": False,
        "quality_v1_admitted": 0, "training_authorized": False,
        "private_values_emitted": False,
    }
    private_file(safe_output, reviewer.canonical(safe) + b"\n")
    return safe


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "reconcile"))
    parser.add_argument("--stage-root", type=Path, required=True)
    parser.add_argument("--review-a-dir", type=Path, required=True)
    parser.add_argument("--review-b-dir", type=Path, required=True)
    parser.add_argument("--c-dir", type=Path, required=True)
    parser.add_argument("--results", type=Path)
    parser.add_argument("--safe-output", type=Path)
    args = parser.parse_args()
    try:
        if args.mode == "prepare":
            result = prepare(args.stage_root, args.review_a_dir,
                             args.review_b_dir, args.c_dir)
        else:
            if args.results is None or args.safe_output is None:
                raise CalibrationHold("C_RESULT_INPUT_MISSING_HOLD")
            result = reconcile(args.stage_root, args.review_a_dir,
                               args.review_b_dir, args.c_dir,
                               args.results, args.safe_output)
        print(reviewer.canonical(result).decode("utf-8"))
        return 0
    except (CalibrationHold, pair.AuditHold, OSError, KeyError, TypeError):
        print(json.dumps({
            "schema": SAFE_SCHEMA, "status": "C_SEMANTIC_CALIBRATION_HOLD",
            "quality_v1_admitted": 0, "training_authorized": False,
            "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
