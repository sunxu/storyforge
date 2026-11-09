"""Prepare a blind second-model advisory packet for R60 P2-A.

Reads only the existing blind packets and Owner adjudication results.
Never reads the prior AI-generated semantic checks or AI advisory files.
Outputs are advisory only and cannot satisfy the Owner semantic-review contract.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import stat
from pathlib import Path
from random import SystemRandom

DIMENSIONS = ("player_agency", "hard_rule", "safety")
PACKET_KEYS = {
    "schema", "calibration_id", "visible_history", "target_text",
    "verified_world_components",
}
RESULT_KEYS = {"schema", "rubric_version", "case_ref", "assessments"}
ADVISORY_SCHEMA = "storyforge_r60_p2a_second_model_cross_review_v1"
EXPECTED_VERDICTS = {"SUPPORTED", "NOT_SUPPORTED", "INSUFFICIENT_CONTEXT"}


class Hold(ValueError):
    pass


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _jsonl(path: Path) -> tuple[list[dict], bytes]:
    raw = path.read_bytes()
    rows = []
    for line_no, line in enumerate(raw.splitlines(), 1):
        try:
            row = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise Hold(f"JSONL_INVALID_LINE_{line_no}") from None
        if not isinstance(row, dict):
            raise Hold(f"JSONL_ROW_NOT_OBJECT_{line_no}")
        rows.append(row)
    return rows, raw


def _secure_directory(path: Path) -> None:
    parent = path.parent
    if not parent.is_dir() or stat.S_IMODE(parent.stat().st_mode) != 0o700:
        raise Hold("OUTPUT_PARENT_PERMISSION_HOLD")
    path.mkdir(mode=0o700, parents=False, exist_ok=False)
    os.chmod(path, 0o700)
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode != 0o700:
        raise Hold("OUTPUT_DIRECTORY_PERMISSION_HOLD")


def _write_private(path: Path, raw: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            path.unlink()
        except OSError:
            pass
        raise
    if stat.S_IMODE(path.stat().st_mode) != 0o600:
        raise Hold("OUTPUT_FILE_PERMISSION_HOLD")


def build(packets: list[dict], results: list[dict], rubric_raw: bytes,
          token_factory=secrets.token_hex) -> tuple[list[dict], dict, dict]:
    if len(packets) != 20 or len(results) != 20:
        raise Hold("P2A_INPUT_CARDINALITY_HOLD")
    packet_by_id = {}
    for packet in packets:
        if set(packet) != PACKET_KEYS or packet.get("schema") != "storyforge_r60_owner_adjudication_packet_v2":
            raise Hold("PACKET_SCHEMA_HOLD")
        ref = packet.get("calibration_id")
        if not isinstance(ref, str) or not ref:
            raise Hold("PACKET_ID_HOLD")
        if ref in packet_by_id:
            raise Hold("PACKET_DUPLICATE_ID_HOLD")
        packet_by_id[ref] = packet

    result_by_id = {}
    for result in results:
        if set(result) != RESULT_KEYS or not isinstance(result.get("assessments"), dict):
            raise Hold("RESULT_SCHEMA_HOLD")
        ref = result.get("case_ref")
        if not isinstance(ref, str) or ref in result_by_id:
            raise Hold("RESULT_ID_HOLD")
        if set(result["assessments"]) != set(DIMENSIONS):
            raise Hold("RESULT_DIMENSION_SET_HOLD")
        result_by_id[ref] = result
    if set(packet_by_id) != set(result_by_id):
        raise Hold("PACKET_RESULT_BINDING_HOLD")

    ids = set()
    mapping = []
    output = []
    for old_id, packet in packet_by_id.items():
        new_id = token_factory(16)
        if (not isinstance(new_id, str) or len(new_id) != 32
                or any(c not in "0123456789abcdef" for c in new_id)
                or new_id in ids or new_id == old_id):
            raise Hold("CROSS_REVIEW_ID_GENERATION_HOLD")
        ids.add(new_id)
        result = result_by_id[old_id]
        targets = {}
        for dimension in DIMENSIONS:
            assessment = result["assessments"][dimension]
            if not isinstance(assessment, dict):
                raise Hold("ASSESSMENT_SHAPE_HOLD")
            verdict = assessment.get("verdict")
            evidence = assessment.get("evidence")
            if verdict not in EXPECTED_VERDICTS or not isinstance(evidence, list):
                raise Hold("ASSESSMENT_CONTENT_HOLD")
            targets[dimension] = {
                "owner_verdict_to_assess": verdict,
                "owner_evidence_to_assess": evidence,
                "owner_rule_basis_to_assess": assessment.get("rule_basis", []),
                "owner_context_coverage_to_assess": assessment.get("context_coverage", {}),
            }
        output.append({
            "schema": ADVISORY_SCHEMA,
            "blind_id": new_id,
            "visible_history": packet["visible_history"],
            "target_text": packet["target_text"],
            "verified_world_components": packet["verified_world_components"],
            "review_targets": targets,
        })
        mapping.append({"blind_id": new_id, "calibration_id": old_id})
    SystemRandom().shuffle(output)
    SystemRandom().shuffle(mapping)
    safe = {
        "schema": "storyforge_r60_p2a_second_model_cross_review_safe_v1",
        "status": "CROSS_REVIEW_PACKET_READY__ADVISORY_ONLY",
        "case_count": len(output),
        "dimension_count": len(output) * len(DIMENSIONS),
        "rubric_sha256": _sha(rubric_raw),
        "prior_ai_semantic_checks_read": False,
        "prior_ai_advisory_files_read": False,
        "owner_results_read_for_entailment_target": True,
        "fresh_blind_ids": True,
        "old_calibration_ids_in_model_packets": False,
        "owner_id_map_separated": True,
        "reviewer_identity_attested": False,
        "owner_review_completed": False,
        "gpu_started": False,
        "hf_jobs_submitted": 0,
        "training_authorized": False,
        "private_values_emitted": False,
    }
    return output, {"schema": "storyforge_r60_p2a_second_model_cross_review_map_v1",
                    "mapping": mapping}, safe


def prompt_text() -> str:
    return """# R60 P2-A：第二模型独立交叉审核（AI Advisory）

你是独立的第二模型审核者。你只收到当前盲包、Owner 对三个维度的 verdict/evidence/rule_basis，以及 Rubric v2.1。你不会收到第一模型的语义复核、AI Advisory 或任何既有复核理由。

逐个案例、逐个维度审核，共 60 项。对每项：
1. 独立阅读完整 visible_history、target_text 和 verified_world_components。
2. 对照 Rubric，判断 Owner verdict 是否被所列全部 evidence 在语义上支持；不要因为 Owner 已给出 verdict 就默认正确。
3. 检查 evidence indexes 是否覆盖该维度的全部 evidence；逐条判断引用是否相关、是否足以支持结论。
4. 特别审查玩家明确拒绝/同意/选择边界、故事已建立硬规则、角色自主性和安全边界。
5. 不得因缺少来源、版权、权利、隐私、授权或数据隔离材料而 HOLD。
6. 证据不足或上下文不完整时，明确列出缺口，使用 INSUFFICIENT_CONTEXT；不得猜测或补造上下文。
7. 不要改写 Owner verdict，不要把你的意见伪装成 Owner 最终裁决。

只输出 60 行 JSONL，每行严格包含：
{"blind_id":"...","dimension":"player_agency|hard_rule|safety","reviewer_type":"AI_CROSS_REVIEW_ADVISORY_NOT_OWNER","conclusion":"SUPPORTS_VERDICT|DOES_NOT_SUPPORT_VERDICT|INSUFFICIENT_CONTEXT","reviewed_evidence_indexes":[0],"reasoning_summary":"...","unresolved_context":["..."]}

每个 blind_id × dimension 恰好一行。reviewed_evidence_indexes 必须列出你实际检查过的全部 evidence indexes；不能只挑选支持结论的引用。若没有可检查的引用，使用 []。reasoning_summary 应简洁具体。不得输出其他字段、Markdown 围栏、汇总文字或身份声明。你的输出仅为 AI Advisory，不是 Owner semantic check，也不能作为 OWNER_INDEPENDENT reviewer 记录。
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packets", required=True, type=Path)
    parser.add_argument("--results", required=True, type=Path)
    parser.add_argument("--rubric", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    try:
        if args.output_dir.exists() or args.output_dir.is_symlink():
            raise Hold("OUTPUT_DIRECTORY_ALREADY_EXISTS_HOLD")
        if (not args.output_dir.parent.is_dir()
                or stat.S_IMODE(args.output_dir.parent.stat().st_mode) != 0o700):
            raise Hold("OUTPUT_PARENT_PERMISSION_HOLD")
        packets, packet_raw = _jsonl(args.packets)
        results, result_raw = _jsonl(args.results)
        rubric_raw = args.rubric.read_bytes()
        output, id_map, safe = build(packets, results, rubric_raw)
        if not args.write:
            safe["status"] = "CROSS_REVIEW_PREFLIGHT_PASS__NO_FILES_WRITTEN"
            safe["files_written"] = 0
            print(json.dumps(safe, sort_keys=True))
            return 0
        _secure_directory(args.output_dir)
        packet_bytes = b"".join(_canonical(x) + b"\n" for x in output)
        map_bytes = _canonical(id_map) + b"\n"
        prompt_bytes = prompt_text().encode()
        manifest = {
            "schema": "storyforge_r60_p2a_second_model_cross_review_manifest_private_v1",
            "status": "CROSS_REVIEW_PACKET_READY__ADVISORY_ONLY",
            "input_packet_sha256": _sha(packet_raw),
            "input_owner_results_sha256": _sha(result_raw),
            "rubric_sha256": _sha(rubric_raw),
            "output_packet_sha256": _sha(packet_bytes),
            "id_map_sha256": _sha(map_bytes),
            "instructions_sha256": _sha(prompt_bytes),
            "case_count": 20,
            "dimension_count": 60,
            "prior_ai_semantic_checks_read": False,
            "prior_ai_advisory_files_read": False,
            "reviewer_identity_attested": False,
            "owner_review_completed": False,
        }
        safe["files_written"] = 6
        files = {
            "AI_CROSS_REVIEW_PACKETS_PRIVATE.jsonl": packet_bytes,
            "AI_CROSS_REVIEW_ID_MAP_PRIVATE.json": map_bytes,
            "AI_CROSS_REVIEW_PROMPT_PRIVATE.md": prompt_bytes,
            "AI_CROSS_REVIEW_MANIFEST_PRIVATE.json": _canonical(manifest) + b"\n",
            "AI_CROSS_REVIEW_SAFE.json": _canonical(safe) + b"\n",
            "RUBRIC_V2_1_PRIVATE.md": rubric_raw,
        }
        for name, raw in files.items():
            _write_private(args.output_dir / name, raw)
        print(json.dumps(safe, sort_keys=True))
        return 0
    except (OSError, Hold, ValueError, TypeError, KeyError) as exc:
        reason = str(exc) if isinstance(exc, Hold) else "INPUT_OR_IO_ERROR"
        print(json.dumps({
            "schema": "storyforge_r60_p2a_second_model_cross_review_safe_v1",
            "status": "CROSS_REVIEW_PACKET_HOLD",
            "reason_code": reason,
            "files_written": 0,
            "private_values_emitted": False,
            "gpu_started": False,
            "training_authorized": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
