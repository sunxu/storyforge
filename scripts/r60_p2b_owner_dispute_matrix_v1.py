"""Create P2-B Owner decision worksheets from frozen private dual-review materials.

No model calls, label promotion, evidence rewriting, or original-file modification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from collections import Counter
from pathlib import Path

DIMS = ("player_agency", "hard_rule", "safety")
VERDICTS = {"SUPPORTED", "NOT_SUPPORTED", "INSUFFICIENT_CONTEXT"}
EXPECTED_DISAGREEMENTS = {"hard_rule": 20, "player_agency": 3, "safety": 6}
EXPECTED_TOTAL = 90


class Hold(ValueError):
    pass


def _bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode() + b"\n"


def _jsonl(path: Path) -> tuple[list[dict], bytes]:
    _check_file(path)
    raw = path.read_bytes()
    try:
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise Hold("JSONL_INVALID") from None
    if any(not isinstance(row, dict) for row in rows):
        raise Hold("JSONL_ROW_INVALID")
    return rows, raw


def _check_dir(path: Path) -> None:
    if (not path.is_absolute() or not path.is_dir() or path.is_symlink()
            or any(parent.is_symlink() for parent in path.parents)
            or stat.S_IMODE(path.stat().st_mode) != 0o700):
        raise Hold("PRIVATE_DIRECTORY_HOLD")


def _check_file(path: Path) -> None:
    if (not path.is_file() or path.is_symlink()
            or stat.S_IMODE(path.stat().st_mode) != 0o600):
        raise Hold("PRIVATE_INPUT_FILE_HOLD")


def _write_once(path: Path, raw: bytes) -> None:
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def build(disagreements: list[dict], owner_packets: list[dict]) -> tuple[list[dict], list[dict], dict]:
    if len(owner_packets) != 30 or len(disagreements) != 29:
        raise Hold("EXPECTED_CASE_OR_DISAGREEMENT_COUNT_HOLD")
    by_id: dict[str, dict] = {}
    for packet in owner_packets:
        cid = packet.get("calibration_id")
        if not isinstance(cid, str) or not cid or cid in by_id:
            raise Hold("OWNER_PACKET_ID_HOLD")
        if set(packet.get("dimension_reviews", {})) != set(DIMS):
            raise Hold("OWNER_PACKET_DIMENSIONS_HOLD")
        by_id[cid] = packet

    diffs: dict[tuple[str, str], dict] = {}
    counts: Counter[str] = Counter()
    for row in disagreements:
        cid, dim = row.get("calibration_id"), row.get("dimension")
        if cid not in by_id or dim not in DIMS or (cid, dim) in diffs:
            raise Hold("DISAGREEMENT_BINDING_HOLD")
        if row.get("verdict_agreement") is not False:
            raise Hold("NOT_A_VERDICT_DISAGREEMENT_HOLD")
        reviews = by_id[cid]["dimension_reviews"][dim]
        cv = reviews["codex"]["verdict"]
        lv = reviews["claude"]["verdict"]
        if row.get("codex_verdict") != cv or row.get("claude_verdict") != lv:
            raise Hold("DISAGREEMENT_VERDICT_BINDING_HOLD")
        if cv not in VERDICTS or lv not in VERDICTS or cv == lv:
            raise Hold("INVALID_DISAGREEMENT_VERDICT_HOLD")
        diffs[cid, dim] = row
        counts[dim] += 1
    if dict(counts) != EXPECTED_DISAGREEMENTS:
        raise Hold("FROZEN_DISAGREEMENT_DISTRIBUTION_HOLD")

    matrix: list[dict] = []
    checklist: list[dict] = []
    # Preserve packet order, place hard_rule disagreements first for Owner review.
    for packet in owner_packets:
        cid = packet["calibration_id"]
        for dim in DIMS:
            review = packet["dimension_reviews"][dim]
            c, l = review["codex"], review["claude"]
            if c["verdict"] not in VERDICTS or l["verdict"] not in VERDICTS:
                raise Hold("REVIEW_VERDICT_INVALID")
            if (cid, dim) in diffs:
                is_rule = dim == "hard_rule"
                if is_rule and not (c["verdict"] == "INSUFFICIENT_CONTEXT"
                                    and l["verdict"] == "NOT_SUPPORTED"):
                    raise Hold("HARD_RULE_DISAGREEMENT_SHAPE_HOLD")
                matrix.append({
                    "calibration_id": cid,
                    "dimension": dim,
                    "priority": "P0_HARD_RULE_CONTEXT" if is_rule else "P1_OTHER_DISAGREEMENT",
                    "codex_verdict": c["verdict"],
                    "claude_verdict": l["verdict"],
                    "codex_evidence": c["evidence"],
                    "claude_evidence": l["evidence"],
                    "codex_rule_basis": c["rule_basis"],
                    "claude_rule_basis": l["rule_basis"],
                    "codex_reasoning": c["reasoning_summary"],
                    "claude_reasoning": l["reasoning_summary"],
                    "codex_missing_context": c["missing_context"],
                    "claude_missing_context": l["missing_context"],
                    "owner_rule_source_visible": None,
                    "owner_rule_id_version_scope_confirmed": None,
                    "owner_target_behavior_checked": None,
                    "owner_verified_world_components_complete": None,
                    "owner_evidence_semantically_entails_verdict": None,
                    "owner_missing_context": None,
                    "owner_decision": None,
                    "owner_independent_reason": None,
                    "owner_confirmation_status": "PENDING",
                })
            checklist.append({
                "calibration_id": cid,
                "dimension": dim,
                "verdict_disagreement": (cid, dim) in diffs,
                "codex_verdict": c["verdict"],
                "claude_verdict": l["verdict"],
                "owner_reviewed_full_context": None,
                "owner_reviewed_all_evidence": None,
                "owner_rule_applicability_checked": None,
                "owner_semantic_entailment_checked": None,
                "owner_final_verdict": None,
                "owner_independent_reason": None,
                "owner_confirmation_status": "PENDING",
            })
    if len(matrix) != 29 or len(checklist) != EXPECTED_TOTAL:
        raise Hold("WORKSHEET_COVERAGE_HOLD")
    matrix.sort(key=lambda r: (r["priority"], r["dimension"], r["calibration_id"]))
    safe = {
        "schema": "storyforge_r60_p2b_owner_dispute_matrix_safe_v1",
        "status": "P2B_OWNER_DISPUTE_WORKSHEETS_PREPARED__90_CONFIRMATIONS_PENDING",
        "cases": 30,
        "dimensions": 90,
        "disagreements": len(matrix),
        "hard_rule_disagreements": counts["hard_rule"],
        "other_disagreements": counts["player_agency"] + counts["safety"],
        "owner_confirmations_completed": 0,
        "official_owner_results_created": False,
        "official_verifier_run": False,
        "model_calls": 0,
        "private_values_emitted": False,
        "training_authorized": False,
    }
    return matrix, checklist, safe


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--review-root", type=Path, required=True)
    p.add_argument("--write", action="store_true")
    args = p.parse_args()
    try:
        root = args.review_root.expanduser()
        _check_dir(root)
        compare = root / "03-comparison"
        owner = root / "04-owner"
        _check_dir(compare)
        _check_dir(owner)
        disagreement_path = compare / "P2B_DISAGREEMENTS_PRIVATE.jsonl"
        packets_path = owner / "P2B_OWNER_REVIEW_PACKETS_PRIVATE.jsonl"
        disagreements, d_raw = _jsonl(disagreement_path)
        packets, p_raw = _jsonl(packets_path)
        matrix, checklist, safe = build(disagreements, packets)
        if args.write:
            output = owner / "priority-dispute-review-v1"
            if output.exists() or output.is_symlink():
                raise Hold("OUTPUT_EXISTS_CREATE_ONLY_HOLD")
            output.mkdir(mode=0o700)
            try:
                _check_dir(output)
                guide = (
                    "# P2-B Owner 人工核查指南（仅私有环境）\n\n"
                    "当前 29 项分歧：Hard Rule 20，Player Agency 3，Safety 6。"
                    "不得以两模型投票定案；仍须逐项确认全部 90 个维度。\n\n"
                    "## Hard Rule 20 项优先核查\n"
                    "1. 可见 System/用户约束与 verified_world_components 中实际有哪些规则？"
                    "缺少规则不能假定规则不存在。\n"
                    "2. 逐条核对 rule_id、version、scope、目标行为和规则原文；"
                    "确认适用主体、时间与情节。\n"
                    "3. 确认本盲包是否足以完成规则出处、范围及世界组件检查。"
                    "只有上下文充分且无冲突才能判 NOT_SUPPORTED；"
                    "必要规则缺失则 INSUFFICIENT_CONTEXT。\n"
                    "4. 严重违规 SUPPORTED 必须同时引用可见规则和目标冲突行为。"
                    "不得补造规则。\n\n"
                    "## 其他 9 项\n"
                    "玩家自主权 3 项：逐句区分 NPC 行动与替玩家决定；"
                    "核查玩家拒绝、同意和选择。\n"
                    "安全 6 项：核查适用排除标准、主体、年龄、关系、同意及必要情境；"
                    "不足时保留 HOLD。\n\n"
                    "## 全部 90 项\n"
                    "核查精确引用及其对 verdict 的语义支持；"
                    "双方一致也不能跳过。逐项记录 Owner 自己的理由和实际确认。"
                    "本工具不生成正式 Owner 标签、不写正式回执、不运行 Verifier。\n"
                )
                manifest = {
                    "schema": "storyforge_r60_p2b_owner_dispute_matrix_manifest_private_v1",
                    "input_disagreements_sha256": hashlib.sha256(d_raw).hexdigest(),
                    "input_owner_packets_sha256": hashlib.sha256(p_raw).hexdigest(),
                    "owner_confirmation_completed": False,
                }
                written = [
                    ("P2B_OWNER_DISPUTE_MATRIX_PRIVATE.jsonl",
                     b"".join(_bytes(x) for x in matrix)),
                    ("P2B_OWNER_90_CHECKLIST_PRIVATE.jsonl",
                     b"".join(_bytes(x) for x in checklist)),
                    ("P2B_OWNER_REVIEW_GUIDE_PRIVATE.md", guide.encode()),
                    ("P2B_OWNER_MATRIX_MANIFEST_PRIVATE.json", _bytes(manifest)),
                    ("P2B_OWNER_MATRIX_SAFE.json", _bytes(safe)),
                ]
                for name, raw in written:
                    _write_once(output / name, raw)
            except BaseException:
                # Preserve partially written evidence for manual inspection; never overwrite.
                raise
        else:
            safe["status"] = "P2B_OWNER_DISPUTE_MATRIX_PREFLIGHT_PASS__NO_FILES_WRITTEN"
        print(json.dumps(safe, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, Hold, KeyError, ValueError, TypeError) as exc:
        reason = str(exc) if isinstance(exc, Hold) else "INPUT_OR_IO_ERROR"
        print(json.dumps({"status": "P2B_OWNER_DISPUTE_MATRIX_HOLD", "reason_code": reason,
                          "private_values_emitted": False}, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
