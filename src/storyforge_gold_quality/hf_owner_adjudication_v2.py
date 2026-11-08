"""Owner-only Gold72 Development-20 blind adjudication packet preparation.

This module reads only the frozen P0 Gold72 manifest and its already-blinded C
source packets. It never reads old A/B/C result files or Owner resolutions,
never stages Locked Regression/R60 Severe10 content, and never calls a model.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import stat
from collections.abc import Callable
from pathlib import Path
from typing import Any

from . import hf_severity_evidence_v2 as severity

P0_GOLD_SCHEMA = "storyforge_r60_gold72_calibration_manifest_private_v1"
SOURCE_PACKET_SCHEMA = "r60_gold72_reviewer_c_blind_story_packet_v1"
PACKET_SCHEMA = "storyforge_r60_owner_adjudication_packet_v2"
MAP_SCHEMA = "storyforge_r60_owner_adjudication_map_private_v2"
MANIFEST_SCHEMA = "storyforge_r60_owner_adjudication_manifest_private_v2"
SAFE_SCHEMA = "storyforge_r60_owner_adjudication_prepare_safe_v2"
SAFE_STATUS = "P2_OWNER_BLIND_PACKETS_READY__OWNER_REVIEW_NOT_STARTED"
PACKET_NAME = "OWNER_ADJUDICATION_BLIND_PACKETS_PRIVATE.jsonl"
MAP_NAME = "OWNER_ADJUDICATION_ID_MAP_PRIVATE.json"
MANIFEST_NAME = "OWNER_ADJUDICATION_MANIFEST_PRIVATE.json"
SAFE_NAME = "OWNER_ADJUDICATION_PREPARE_SAFE.json"
INSTRUCTIONS_NAME = "OWNER_ADJUDICATION_INSTRUCTIONS_CN.md"
SCHEMA_NAME = "OWNER_ADJUDICATION_SCHEMA_V2.json"
MAX_INPUT_BYTES = 64 * 1024 * 1024
FORBIDDEN_PACKET_KEYS = {
    "blind_case_id", "blind_id", "prior_b2_blind_case_id",
    "original_case_id", "original_story_uuid", "story_uuid",
    "reviewer_a_decision", "reviewer_b2_decision", "reviewer_c_decision",
    "owner_decision", "reviewer_a", "reviewer_b", "reviewer_c",
    "severe_flags", "scores", "disagreement_type", "slot", "source_index",
    "case_id", "cohort", "owner_resolution",
}


class AdjudicationHold(ValueError):
    """Stable reason code; never includes private values."""


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise AdjudicationHold("DUPLICATE_JSON_KEY")
        out[key] = value
    return out


def _json(raw: bytes, reason: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs)
    except (UnicodeError, json.JSONDecodeError):
        raise AdjudicationHold(reason) from None
    if not isinstance(value, dict):
        raise AdjudicationHold(reason)
    return value


def _jsonl(raw: bytes, reason: str) -> list[dict[str, Any]]:
    try:
        rows = [
            json.loads(line, object_pairs_hook=_pairs)
            for line in raw.decode("utf-8").splitlines() if line.strip()
        ]
    except (UnicodeError, json.JSONDecodeError):
        raise AdjudicationHold(reason) from None
    if not rows or any(not isinstance(row, dict) for row in rows):
        raise AdjudicationHold(reason)
    return rows


def _unique(rows: list[dict[str, Any]], field: str, reason: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for row in rows:
        value = row.get(field)
        if not isinstance(value, str) or not value or value in out:
            raise AdjudicationHold(reason)
        out[value] = row
    return out


def _walk_keys(value: object):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _walk_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_keys(item)


def _validate_manifest(manifest: dict, source_packet_raw: bytes) -> list[dict]:
    if (manifest.get("schema") != P0_GOLD_SCHEMA
            or manifest.get("status") != "GOLD72_CALIBRATION_MANIFEST_FROZEN"
            or manifest.get("candidate_count") != 40
            or manifest.get("development_case_count") != 20
            or manifest.get("locked_regression_case_count") != 20
            or manifest.get("story_disjoint") is not False
            or manifest.get("quality_v1_admitted") != 0
            or manifest.get("training_authorized") is not False):
        raise AdjudicationHold("P0_GOLD_MANIFEST_NOT_FROZEN")
    pins = manifest.get("source_pins_sha256")
    if (not isinstance(pins, dict)
            or pins.get("c_blind") != sha(source_packet_raw)):
        raise AdjudicationHold("P0_GOLD_C_BLIND_SOURCE_PIN_MISMATCH")
    development = manifest.get("development_cases")
    locked = manifest.get("locked_regression_cases")
    if (not isinstance(development, list) or len(development) != 20
            or any(not isinstance(row, dict) for row in development)
            or not isinstance(locked, list) or len(locked) != 20
            or any(not isinstance(row, dict) for row in locked)
            or any(row.get("split") != "development" for row in development)
            or any(row.get("split") != "locked_regression" for row in locked)):
        raise AdjudicationHold("P0_GOLD_SPLIT_MANIFEST_INVALID")
    if len({row.get("blind_case_id") for row in development}) != 20:
        raise AdjudicationHold("P0_GOLD_DEVELOPMENT_ID_DUPLICATE")
    if len({row.get("target_sha256") for row in development}) != 20:
        raise AdjudicationHold("P0_GOLD_DEVELOPMENT_TARGET_DUPLICATE")
    return development


def _source_cases(source_packets: list[dict]) -> list[dict]:
    cases: list[dict] = []
    for packet in source_packets:
        if (packet.get("schema") != SOURCE_PACKET_SCHEMA
                or packet.get("reviewer") != "C"
                or not isinstance(packet.get("cases"), list)):
            raise AdjudicationHold("GOLD_C_BLIND_SOURCE_SCHEMA_INVALID")
        cases.extend(packet["cases"])
    if len(cases) != 40:
        raise AdjudicationHold("GOLD_C_BLIND_SOURCE_COUNT_INVALID")
    return cases


def build_package(
    manifest: dict, source_packet_raw: bytes, *,
    p0_manifest_sha256: str | None = None,
    token_factory: Callable[[], str] | None = None,
    shuffle: Callable[[list[Any]], None] | None = None,
) -> tuple[bytes, dict, dict, dict, bytes]:
    development = _validate_manifest(manifest, source_packet_raw)
    source_packets = _jsonl(source_packet_raw, "GOLD_C_BLIND_SOURCE_JSONL_INVALID")
    cases = _source_cases(source_packets)
    source_by_id = _unique(cases, "blind_case_id", "GOLD_C_SOURCE_ID_DUPLICATE")
    source_by_target = _unique(cases, "target_sha256", "GOLD_C_SOURCE_TARGET_DUPLICATE")
    if len(source_by_id) != 40 or len(source_by_target) != 40:
        raise AdjudicationHold("GOLD_C_SOURCE_COVERAGE_INVALID")

    token_factory = token_factory or (lambda: secrets.token_hex(16))
    shuffle = shuffle or secrets.SystemRandom().shuffle
    packets: list[dict] = []
    mapping: list[dict] = []
    used_ids: set[str] = set()
    for row in development:
        old_id = row.get("blind_case_id")
        target_sha = row.get("target_sha256")
        source = source_by_id.get(old_id)
        if (source is None or source_by_target.get(target_sha) is not source
                or source.get("target_sha256") != target_sha):
            raise AdjudicationHold("GOLD_DEVELOPMENT_SOURCE_BINDING_HOLD")
        history = source.get("history")
        current_user_text = source.get("current_user_text")
        target_text = source.get("target_assistant_text")
        if (not isinstance(history, list) or not history
                or not isinstance(current_user_text, str) or not current_user_text.strip()
                or not isinstance(target_text, str) or not target_text.strip()
                or sha(target_text.encode("utf-8")) != target_sha):
            raise AdjudicationHold("GOLD_DEVELOPMENT_CONTEXT_INVALID")
        visible_history = list(history) + [
            {"role": "user", "content": current_user_text}
        ]
        if any(
            not isinstance(message, dict)
            or set(message) != {"role", "content"}
            or message.get("role") not in ("system", "user", "assistant")
            or not isinstance(message.get("content"), str)
            for message in visible_history
        ):
            raise AdjudicationHold("GOLD_DEVELOPMENT_HISTORY_INVALID")
        new_id = token_factory()
        if (not isinstance(new_id, str) or len(new_id) != 32
                or any(char not in "0123456789abcdef" for char in new_id)
                or new_id in used_ids or new_id == old_id):
            raise AdjudicationHold("OWNER_ADJUDICATION_ID_INVALID")
        used_ids.add(new_id)
        packet = {
            "schema": PACKET_SCHEMA,
            "calibration_id": new_id,
            "visible_history": visible_history,
            "target_text": target_text,
            # P0 source packet has no verified component snapshot. Do not infer one.
            "target_semantics": "DB_FINAL_PERSISTED_ASSISTANT",
            "verified_world_components": [],
        }
        if FORBIDDEN_PACKET_KEYS & set(_walk_keys(packet)):
            raise AdjudicationHold("OWNER_ADJUDICATION_PRIOR_LABEL_LEAK")
        packets.append(packet)
        mapping.append({
            "calibration_id": new_id,
            "private_case_ref": old_id,
            "target_sha256": target_sha,
            "private_story_ref": row.get("original_story_uuid"),
            "disagreement_stratum": row.get("disagreement_type"),
        })

    if len(packets) != 20 or len(mapping) != 20:
        raise AdjudicationHold("OWNER_ADJUDICATION_CASE_COUNT_INVALID")
    shuffle(packets)
    packet_raw = b"".join(canonical(packet) + b"\n" for packet in packets)
    private_map = {
        "schema": MAP_SCHEMA,
        "status": "OWNER_ONLY_PRIVATE_MAPPING",
        "case_count": 20,
        "mapping": mapping,
    }
    private_map["receipt_sha256"] = sha(canonical(private_map))
    rubric_raw = severity.RUBRIC_TEXT.encode("utf-8")
    manifest_out = {
        "schema": MANIFEST_SCHEMA,
        "status": "OWNER_ADJUDICATION_PACKET_SET_FROZEN__REVIEW_NOT_STARTED",
        "rubric_version": severity.RUBRIC_VERSION,
        "source_p0_manifest_sha256": p0_manifest_sha256 or sha(canonical(manifest)),
        "source_c_blind_packets_sha256": sha(source_packet_raw),
        "rubric_sha256": sha(rubric_raw),
        "packet_sha256": sha(packet_raw),
        "owner_map_sha256": sha(canonical(private_map)),
        "case_count": 20,
        "locked_regression_case_count": 20,
        "locked_regression_cases_in_packets": 0,
        "r60_severe10_cases_in_packets": 0,
        "old_a_b_c_judgments_embedded": False,
        "old_owner_resolution_embedded": False,
        "old_blind_ids_embedded": False,
        "source_story_ids_embedded": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "private_values_emitted": False,
    }
    manifest_out["receipt_sha256"] = sha(canonical(manifest_out))
    instructions = f"""# Gold72 Development 20：Owner 独立盲裁决

Rubric：{severity.RUBRIC_VERSION}  
Schema：{severity.SCHEMA}

## 只允许读取
- `{PACKET_NAME}`
- 本说明
- 已冻结的公开 Rubric v2

不要打开 Owner ID Map、P0 Gold manifest、Gold72 C 旧结果、A V3/B2 结果、历史 Owner resolution 或任何旧 checkpoint。不要查看 Locked Regression 20 或 R60 Severe10。

## 裁决要求
1. 每个 packet 的三个维度分别给出 SUPPORTED / NOT_SUPPORTED / INSUFFICIENT_CONTEXT。
2. 严格按 Rubric v2 输出 evidence locator、连续原文、rule_basis、reasoning_summary、missing_context、context_coverage、confidence。
3. NPC 主动行动不自动等于玩家代理；普通亲密、冲突或威胁台词不自动等于安全排除。
4. 规则、版本、适用范围或主体/同意/年龄等上下文不足时，必须 INSUFFICIENT_CONTEXT；不要猜测。
5. 只使用 packet 中的新 `calibration_id`。不得尝试恢复旧 blind ID、Story ID 或来源映射。
6. 不要为了让 20 条都得到确定标签而降低证据标准。

## 输出
1. 生成 20 行 `OWNER_ADJUDICATION_RESULTS_PRIVATE.jsonl`。每行符合 `{severity.SCHEMA}`，case_ref 使用 packet 的 calibration_id，rubric_version 固定为 `{severity.RUBRIC_VERSION}`。
2. 完成 verdict/evidence 后，再单独进行 semantic entailment 复核，生成 60 行 `OWNER_SEMANTIC_ENTAILMENT_CHECKS_PRIVATE.jsonl`（每个 case × 三维一行）。每行外层包含 calibration_id、dimension、reviewed_at_utc 和 check；check 必须符合 `{severity.SEMANTIC_CHECK_SCHEMA}`。结论使用 SUPPORTS_VERDICT / DOES_NOT_SUPPORT_VERDICT / INSUFFICIENT_CONTEXT。INSUFFICIENT_CONTEXT 且无引用时 reviewed_evidence_indexes 可以为空数组。
3. 不得把引用存在性当成语义蕴含；DOES_NOT_SUPPORT_VERDICT 或未解决的上下文不足均保留 HOLD，不得为凑数改判。
4. 两个文件均留在 Owner 私有目录；不要复制源正文、结果或映射到 SAFE/GitHub。

本次只完成 Owner 独立裁决，不执行模型推理，不运行 HF Job/GPU，不处理 Locked Regression 20、R60 Severe10、1000 条候选或 SFT。
"""
    safe = {
        "schema": SAFE_SCHEMA,
        "status": SAFE_STATUS,
        "cases_prepared": 20,
        "gold72_development_cases_only": True,
        "gold72_locked_regression_cases_exposed": False,
        "r60_severe10_cases_exposed": False,
        "old_a_b_c_judgments_exposed": False,
        "old_owner_resolution_exposed": False,
        "old_blind_ids_exposed": False,
        "private_values_emitted": False,
        "owner_review_started": False,
        "model_calls": 0,
        "hf_jobs_submitted": 0,
        "gpu_started": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
    }
    return packet_raw, private_map, manifest_out, safe, instructions.encode("utf-8")


def _read_private(path: Path, repo_root: Path, limit: int = MAX_INPUT_BYTES) -> bytes:
    if not path.is_absolute() or any(parent.is_symlink() for parent in (path, *path.parents)):
        raise AdjudicationHold("PRIVATE_INPUT_PATH_INVALID")
    try:
        resolved = path.resolve(strict=True)
        info = path.lstat()
    except OSError:
        raise AdjudicationHold("PRIVATE_INPUT_MISSING") from None
    if resolved == repo_root or repo_root in resolved.parents:
        raise AdjudicationHold("PRIVATE_INPUT_INSIDE_REPOSITORY")
    if (not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= limit
            or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1
            or stat.S_IMODE(path.parent.stat().st_mode) != 0o700):
        raise AdjudicationHold("PRIVATE_INPUT_PERMISSION_OR_SIZE_HOLD")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
            raise AdjudicationHold("PRIVATE_INPUT_CHANGED_DURING_OPEN")
        raw = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
    if (not 0 < len(raw) <= limit
            or (after.st_size, after.st_mtime_ns) != (opened.st_size, opened.st_mtime_ns)):
        raise AdjudicationHold("PRIVATE_INPUT_CHANGED_DURING_READ")
    return raw


def _write_once(path: Path, raw: bytes) -> None:
    fd = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        stat.S_IRUSR | stat.S_IWUSR,
    )
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o600)


def prepare(
    p0_manifest_path: Path, source_packet_path: Path,
    output_dir: Path, repo_root: Path, *, dry_run: bool = True,
) -> dict:
    repo_root = repo_root.resolve(strict=True)
    p0_raw = _read_private(p0_manifest_path, repo_root, 8 * 1024 * 1024)
    source_raw = _read_private(source_packet_path, repo_root, 32 * 1024 * 1024)
    manifest = _json(p0_raw, "P0_GOLD_MANIFEST_JSON_INVALID")
    packet_raw, private_map, manifest_out, safe, instructions = build_package(
        manifest, source_raw, p0_manifest_sha256=sha(p0_raw)
    )
    if dry_run:
        safe["status"] = "P2_OWNER_BLIND_PACKET_PREFLIGHT_PASS__NO_FILES_WRITTEN"
        safe["files_written"] = 0
        return safe
    output_dir = output_dir.expanduser()
    if (not output_dir.is_absolute() or output_dir.exists() or output_dir.is_symlink()
            or any(parent.is_symlink() for parent in output_dir.parents)
            or not output_dir.parent.is_dir()
            or stat.S_IMODE(output_dir.parent.stat().st_mode) != 0o700
            or output_dir.resolve(strict=False) == repo_root
            or repo_root in output_dir.resolve(strict=False).parents):
        raise AdjudicationHold("PRIVATE_OUTPUT_DIRECTORY_HOLD")
    output_dir.mkdir(mode=0o700)
    output_dir.chmod(0o700)
    safe["files_written"] = 6
    outputs = [
        (PACKET_NAME, packet_raw),
        (MAP_NAME, canonical(private_map) + b"\n"),
        (MANIFEST_NAME, canonical(manifest_out) + b"\n"),
        (SAFE_NAME, canonical(safe) + b"\n"),
        (INSTRUCTIONS_NAME, instructions),
        (SCHEMA_NAME, canonical(severity.response_schema_v2()) + b"\n"),
    ]
    created: list[Path] = []
    try:
        for filename, raw in outputs:
            target = output_dir / filename
            _write_once(target, raw)
            created.append(target)
        if (stat.S_IMODE(output_dir.stat().st_mode) != 0o700
                or any(stat.S_IMODE(path.stat().st_mode) != 0o600 for path in created)):
            raise AdjudicationHold("PRIVATE_OUTPUT_PERMISSION_POSTCHECK_HOLD")
    except BaseException:
        for path in reversed(created):
            path.unlink(missing_ok=True)
        raise
    return safe
