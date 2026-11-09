"""P2-B independent Locked20 + Severe10 packets. Owner private, no inference."""
from __future__ import annotations

import secrets
import stat
from pathlib import Path

from . import hf_owner_adjudication_v2 as base
from . import hf_severity_evidence_v2 as severity

PACKET_SCHEMA = "storyforge_r60_p2b_owner_packet_private_v1"
MANIFEST_SCHEMA = "storyforge_r60_p2b_manifest_private_v1"
MAP_SCHEMA = "storyforge_r60_p2b_map_private_v1"
SAFE_SCHEMA = "storyforge_r60_p2b_prepare_safe_v1"
PACKET_NAME = "P2B_BLIND_PACKETS_PRIVATE.jsonl"
MAP_NAME = "P2B_ID_MAP_PRIVATE.json"
MANIFEST_NAME = "P2B_MANIFEST_PRIVATE.json"
SAFE_NAME = "P2B_PREPARE_SAFE.json"
RESULT_NAME = "P2B_OWNER_RESULTS_PRIVATE.jsonl"
CHECK_NAME = "P2B_SEMANTIC_CHECKS_PRIVATE.jsonl"


def build_package(gold: dict, severe: dict, dedup: dict,
                  gold_raw: bytes, severe_raw: bytes, *,
                  token_factory=None, shuffle=None):
    """Require exact 20/10 frozen bindings; no prior verdict enters a packet."""
    if (gold.get("schema") != base.P0_GOLD_SCHEMA
            or gold.get("status") != "GOLD72_CALIBRATION_MANIFEST_FROZEN"
            or gold.get("candidate_count") != 40
            or gold.get("development_case_count") != 20
            or gold.get("locked_regression_case_count") != 20
            or gold.get("story_disjoint") is not False
            or gold.get("source_pins_sha256", {}).get("c_blind") != base.sha(gold_raw)
            or severe.get("schema") != "storyforge_r60_severe10_calibration_manifest_private_v1"
            or severe.get("status") != "R60_SEVERE10_CALIBRATION_MANIFEST_FROZEN"
            or severe.get("candidate_count") != 10
            or severe.get("unique_source_cases") != 10
            or severe.get("source_pins_sha256", {}).get("c_packets") != base.sha(severe_raw)
            or dedup.get("schema") != "storyforge_r60_calibration_crossset_dedup_private_v1"
            or dedup.get("status") != "CROSSSET_EXACT_DEDUP_PASS"
            or any(dedup.get("exact_" + k + "_overlap_count", 0) != 0
                   for k in ("history", "target", "full"))
            or any(x.get("training_authorized") is not False
                   or x.get("quality_v1_admitted") != 0 for x in (gold, severe))):
        raise base.AdjudicationHold("P2B_P0_FREEZE_BINDING_HOLD")
    locked = gold.get("locked_regression_cases")
    development = gold.get("development_cases")
    severe_cases = severe.get("cases")
    if (not isinstance(locked, list) or len(locked) != 20
            or not isinstance(development, list) or len(development) != 20
            or not isinstance(severe_cases, list) or len(severe_cases) != 10
            or any(x.get("split") != "locked_regression" for x in locked)
            or any(x.get("split") != "development" for x in development)):
        raise base.AdjudicationHold("P2B_FROZEN_COHORT_COUNT_HOLD")
    sources = base._source_cases(base._jsonl(gold_raw, "P2B_GOLD_SOURCE_JSONL_HOLD"))
    gold_index = base._unique(sources, "blind_case_id", "P2B_GOLD_SOURCE_ID_HOLD")
    pilot_rows = base._jsonl(severe_raw, "P2B_SEVERE_SOURCE_JSONL_HOLD")
    severe_index = base._unique(pilot_rows, "calibration_id", "P2B_SEVERE_SOURCE_ID_HOLD")
    if len(gold_index) != 40 or len(severe_index) != 10:
        raise base.AdjudicationHold("P2B_SOURCE_COVERAGE_HOLD")
    dev_refs = {x["blind_case_id"] for x in development}
    if len(dev_refs) != 20 or dev_refs & {x.get("blind_case_id") for x in locked}:
        raise base.AdjudicationHold("P2B_DEVELOPMENT_OVERLAP_HOLD")

    token_factory = token_factory or (lambda: secrets.token_hex(16))
    shuffle = shuffle or secrets.SystemRandom().shuffle
    output = []
    mapping = []
    used = set()
    for cohort, entries in (("locked_regression", locked), ("severe10", severe_cases)):
        for entry in entries:
            old_id = entry.get("blind_case_id") if cohort == "locked_regression" else entry.get("calibration_id")
            src = (gold_index if cohort == "locked_regression" else severe_index).get(old_id)
            if src is None:
                raise base.AdjudicationHold("P2B_SOURCE_BINDING_HOLD")
            if cohort == "locked_regression":
                target = src.get("target_assistant_text")
                history = src.get("history")
                current_user = src.get("current_user_text")
                if (src.get("target_sha256") != entry.get("target_sha256")
                        or not isinstance(current_user, str) or not current_user.strip()
                        or not isinstance(history, list)):
                    raise base.AdjudicationHold("P2B_GOLD_TARGET_BINDING_HOLD")
                history = history + [{"role": "user", "content": current_user}]
                target_sha = entry["target_sha256"]
            else:
                history = src.get("visible_history")
                target = src.get("target_text")
                target_sha = base.sha(target.encode("utf-8")) if isinstance(target, str) else None
                if src.get("schema") != "storyforge_r60_pilot10_c_blind_packet_private_v1":
                    raise base.AdjudicationHold("P2B_SEVERE_SOURCE_SCHEMA_HOLD")
            if (not isinstance(target, str) or not target.strip()
                    or not isinstance(history, list) or not history
                    or base.sha(target.encode("utf-8")) != target_sha):
                raise base.AdjudicationHold("P2B_TARGET_INVALID")
            visible = []
            for msg in history:
                if (not isinstance(msg, dict)
                        or msg.get("role") not in ("system", "user", "assistant")
                        or not isinstance(msg.get("content"), str)):
                    raise base.AdjudicationHold("P2B_HISTORY_INVALID")
                visible.append({"role": msg["role"], "content": msg["content"]})
            new_id = token_factory()
            if (not isinstance(new_id, str) or len(new_id) != 32
                    or any(c not in "0123456789abcdef" for c in new_id)
                    or new_id in used or new_id == old_id):
                raise base.AdjudicationHold("P2B_NEW_BLIND_ID_INVALID")
            used.add(new_id)
            packet = {
                "schema": PACKET_SCHEMA, "calibration_id": new_id,
                "visible_history": visible, "target_text": target,
                "verified_world_components": [],
            }
            if base.FORBIDDEN_PACKET_KEYS & set(base._walk_keys(packet)):
                raise base.AdjudicationHold("P2B_PRIOR_LABEL_LEAK_HOLD")
            output.append(packet)
            mapping.append({
                "calibration_id": new_id, "cohort": cohort,
                "private_case_ref": old_id, "target_sha256": target_sha,
                "packet_sha256": base.sha(base.canonical(packet)),
            })
    if len(output) != 30 or len(used) != 30:
        raise base.AdjudicationHold("P2B_CASE_COUNT_HOLD")
    shuffle(output)
    raw = b"".join(base.canonical(p) + b"\n" for p in output)
    private_map = {"schema": MAP_SCHEMA, "case_count": 30, "mapping": mapping}
    private_map["receipt_sha256"] = base.sha(base.canonical(private_map))
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "status": "P2B_HELDOUT_PACKETS_FROZEN__OWNER_REVIEW_NOT_STARTED",
        "rubric_version": severity.RUBRIC_VERSION,
        "case_count": 30,
        "cohort_counts": {"locked_regression": 20, "severe10": 10},
        "packet_sha256": base.sha(raw),
        "owner_map_sha256": base.sha(base.canonical(private_map)),
        "rubric_sha256": base.sha(severity.RUBRIC_TEXT.encode("utf-8")),
        "old_owner_labels_exposed": False,
        "development_cases_exposed": False,
        "owner_review_started": False,
        "training_authorized": False, "gpu_started": False,
        "quality_v1_admitted": 0, "private_values_emitted": False,
    }
    manifest["receipt_sha256"] = base.sha(base.canonical(manifest))
    safe = {
        "schema": SAFE_SCHEMA,
        "status": "P2B_BLIND_PACKETS_READY__OWNER_REVIEW_NOT_STARTED",
        "cases_prepared": 30, "semantic_checks_expected": 90,
        "cohort_counts": {"locked_regression": 20, "severe10": 10},
        "development_cases_exposed": False, "old_owner_labels_exposed": False,
        "owner_review_started": False, "model_calls": 0, "hf_jobs_submitted": 0,
        "training_authorized": False, "gpu_started": False,
        "quality_v1_admitted": 0, "private_values_emitted": False,
    }
    return raw, private_map, manifest, safe


def prepare(gold_path: Path, severe_path: Path, dedup_path: Path,
            gold_source_path: Path, severe_source_path: Path,
            out_dir: Path, repo_root: Path, *, dry_run: bool = True):
    repo = repo_root.resolve(strict=True)
    gold_raw = base._read_private(gold_path, repo, 8 * 1024 * 1024)
    severe_raw = base._read_private(severe_path, repo, 8 * 1024 * 1024)
    dedup_raw = base._read_private(dedup_path, repo, 8 * 1024 * 1024)
    gold_source = base._read_private(gold_source_path, repo, 32 * 1024 * 1024)
    severe_source = base._read_private(severe_source_path, repo, 32 * 1024 * 1024)
    raw, mapping, manifest, safe = build_package(
        base._json(gold_raw, "P2B_GOLD_MANIFEST_JSON_HOLD"),
        base._json(severe_raw, "P2B_SEVERE_MANIFEST_JSON_HOLD"),
        base._json(dedup_raw, "P2B_DEDUP_JSON_HOLD"),
        gold_source, severe_source,
    )
    out_dir = out_dir.expanduser()
    if (not out_dir.is_absolute() or out_dir.exists() or out_dir.is_symlink()
            or any(p.is_symlink() for p in out_dir.parents)
            or not out_dir.parent.is_dir()
            or stat.S_IMODE(out_dir.parent.stat().st_mode) != 0o700
            or out_dir.resolve(strict=False) == repo
            or repo in out_dir.resolve(strict=False).parents):
        raise base.AdjudicationHold("P2B_OUTPUT_DIRECTORY_HOLD")
    if dry_run:
        return {**safe, "status": "P2B_PREFLIGHT_PASS__NO_FILES_WRITTEN", "files_written": 0}
    out_dir.mkdir(mode=0o700)
    outputs = (
        (PACKET_NAME, raw),
        (MAP_NAME, base.canonical(mapping) + b"\n"),
        (MANIFEST_NAME, base.canonical(manifest) + b"\n"),
        (SAFE_NAME, base.canonical({**safe, "files_written": 6}) + b"\n"),
        ("P2B_OWNER_INSTRUCTIONS_CN.md", (
            "# P2-B 独立 held-out Owner 盲审\n\n"
            "只读 P2B_BLIND_PACKETS_PRIVATE.jsonl，不读映射、旧结果或先前模型标签。"
            "按 Rubric v2.1 逐案输出 30 条 Owner 结果、90 条独立语义复核。"
            "仅评估三维内容语义，不审核来源、版权、授权或隐私证明。"
            "结果只存 Owner 私有目录，不向模型或 GitHub 提供。"
            "每条语义复核使用与 P2-A 相同的 4 字段外层和 7 字段 check；"
            "真实不足保留 HOLD。不得启动推理或训练。\n"
        ).encode("utf-8")),
        ("P2B_OWNER_SCHEMA_V2.json", base.canonical(severity.response_schema_v2()) + b"\n"),
    )
    created = []
    try:
        for name, body in outputs:
            target = out_dir / name
            base._write_once(target, body)
            created.append(target)
    except BaseException:
        for target in reversed(created):
            target.unlink(missing_ok=True)
        raise
    return {**safe, "files_written": 6}


def verify(packet_raw: bytes, result_raw: bytes, check_raw: bytes):
    manifest, safe = base.verify_owner_results(
        packet_raw, result_raw, check_raw,
        expected_cases=30, packet_schema=PACKET_SCHEMA,
    )
    manifest["schema"] = "storyforge_r60_p2b_owner_results_manifest_private_v1"
    manifest["status"] = "P2B_OWNER_REVIEW_COMPLETE__SEMANTIC_HOLDS_PRESERVED"
    manifest["receipt_sha256"] = base.sha(base.canonical({
        k: v for k, v in manifest.items() if k != "receipt_sha256"
    }))
    safe["schema"] = "storyforge_r60_p2b_owner_results_safe_v1"
    safe["status"] = "P2B_OWNER_REVIEW_COMPLETE__SEMANTIC_HOLDS_PRESERVED"
    return manifest, safe
