"""R48: CPU-only four-arm Gold/Base/v0.1/v0.2 retrospective blind review.

Consumes immutable v0.1 compiled Test, frozen 20 prompts, and the existing
completed R47 model inference outputs. Does not use old reviewer ratings,
model answer maps or any training/generation capability.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import secrets
from pathlib import Path

from v02_r47_eval_validate import validate_prompts, validate_responses

ARMS = ("gold", "base", "v01", "v02")
DIMS = ("剧情连续性", "角色一致性", "指令遵循", "文学表现力", "互动推进", "玩家自主权")
RUN_KEY = "r47-20261014T091647Z-637890"
BASE_SHA256 = "becd890268edb1002c3f7195a1906f73045a86643fdac45eaf7090ee82d4dcfe"
CANONICAL_TEST_SHA256 = "d8eee6db5882d85dce7ffc01256e7c5b9b46e133bdb2cf8591259112b92e980d"
R47_STATUS = "R47_THREE_MODEL_REGRESSION_GENERATION_PASS_NOT_PROMOTED"
SOURCE_COLS = (
    "样本编号", "故事背景与系统规则", "历史对话", "当前用户输入",
    "回复A", "回复B", "回复C", "回复D",
)
EVAL_COLS = (
    "整体最佳(A/B/C/D/TIE)", "评分理由与逐字证据",
    "严重问题与对应回复", "玩家自主权严重侵犯(A/B/C/D/无)",
)
SCORE_COLS = tuple(f"{dim}·{label}" for dim in DIMS for label in "ABCD")
COLUMNS = SOURCE_COLS + EVAL_COLS + SCORE_COLS


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            digest.update(block)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_gold(compiled_test: Path, prompts: list[dict]) -> list[str]:
    """Reconcile each canonical author reply against the complete frozen prompt."""
    rows = read_jsonl(compiled_test)
    if len(rows) != 20:
        raise ValueError(f"expected 20 canonical compiled Test rows, got {len(rows)}")
    targets = []
    for index, (record, prompt) in enumerate(zip(rows, prompts, strict=True)):
        dialogue = record.get("messages")
        if not isinstance(dialogue, list) or len(dialogue) < 3:
            raise ValueError(f"source row {index} has no complete history")
        if dialogue[-2].get("role") != "user" or dialogue[-1].get("role") != "assistant":
            raise ValueError(f"source row {index} has invalid final original reply")
        original_context = [
            {"role": msg.get("role"), "content": msg.get("content")}
            for msg in dialogue[:-1]
        ]
        if original_context != prompt["messages"]:
            raise ValueError(f"original Gold prompt mismatch, case {index}")
        target = dialogue[-1].get("content")
        if not isinstance(target, str) or not target.strip():
            raise ValueError(f"empty canonical author reply, case {index}")
        targets.append(target)
    return targets


def check_r47(report_path: Path, prompts_path: Path, manifest_path: Path,
              model_files: dict[str, Path], prompts: list[dict]) -> dict[str, list[str]]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if (report.get("status") != R47_STATUS
            or report.get("run_key") != RUN_KEY
            or report.get("generation_complete") is not True
            or report.get("completed_arms") != ["base", "v01", "v02"]
            or report.get("training_performed") is not False
            or report.get("fresh_heldout") is not False
            or report.get("promotion_approved") is not False):
        raise ValueError("R47 three-arm source report not complete or wrong run")
    observed = report.get("input") or {}
    if (observed.get("count") != 20
            or observed.get("prompts_sha256") != sha(prompts_path)
            or observed.get("manifest_sha256") != sha(manifest_path)):
        raise ValueError("source R47 Test prompt identity mismatch")
    reused = report.get("reused_base") or {}
    if reused.get("sha256") != BASE_SHA256 or reused.get("run_key") != "r47-20261014T082109Z-820409":
        raise ValueError("R47 Base source identity changed")
    outputs = {}
    for arm in ("base", "v01", "v02"):
        path = model_files[arm]
        if (report.get("results_sha256") or {}).get(arm) != sha(path):
            raise ValueError(f"R47 {arm} output SHA mismatch")
        outputs[arm] = validate_responses(path, prompts)
        if len(outputs[arm]) != 20:
            raise ValueError(f"R47 {arm} does not have 20 responses")
    if sha(model_files["base"]) != BASE_SHA256:
        raise ValueError("salvaged Base bytes mutated")
    return outputs


def context_text(msgs: list[dict], kind: str) -> str:
    subset = (
        [m for m in msgs if m["role"] in ("system", "developer")]
        if kind == "background"
        else [m for m in msgs[:-1] if m["role"] not in ("system", "developer")]
    )
    return "\n\n".join(f"【{m['role']}】\n{m['content']}" for m in subset)


def build(*, compiled_test: Path, prompts_file: Path, manifest_file: Path,
          report_file: Path, model_files: dict[str, Path], output: Path) -> dict:
    if output.exists():
        raise FileExistsError("R48 output already exists; never overwrite a blind pack")
    if sha(compiled_test) != CANONICAL_TEST_SHA256:
        raise ValueError("v0.1 canonical 20-case original Test file SHA256 mismatch")
    prompts, manifest_entries = validate_prompts(prompts_file, manifest_file)
    original = read_gold(compiled_test, prompts)
    model_results = check_r47(
        report_file, prompts_file, manifest_file, model_files, prompts
    )
    arms = {"gold": original, **model_results}
    output.mkdir(parents=True, exist_ok=False)
    review_dir = output / "reviewers"
    private_dir = output / "coordinator" / "private"
    review_dir.mkdir(parents=True)
    private_dir.mkdir(parents=True)
    rows: list[dict] = []
    blind_rows: list[dict] = []
    answer_key: list[dict] = []
    for index, (prompt, entry) in enumerate(zip(prompts, manifest_entries, strict=True)):
        order = list(ARMS)
        secrets.SystemRandom().shuffle(order)
        mapping = dict(zip("ABCD", order, strict=True))
        answer_key.append({"sample_id": entry["sample_id"], "mapping": mapping})
        visible = {
            f"回复{letter}": arms[arm][index]
            for letter, arm in mapping.items()
        }
        msgs = prompt["messages"]
        rows.append({
            "样本编号": entry["sample_id"],
            "故事背景与系统规则": context_text(msgs, "background"),
            "历史对话": context_text(msgs, "history"),
            "当前用户输入": msgs[-1]["content"],
            **visible,
        })
        blind_rows.append({
            "sample_id": entry["sample_id"],
            "prompt_sha256": entry["prompt_sha256"],
            **{f"response_{letter.lower()}": visible[f"回复{letter}"] for letter in "ABCD"},
        })
    for i in (1, 2, 3):
        path = review_dir / f"R48_Reviewer_{i:02d}.csv"
        with path.open("x", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
    blind_path = review_dir / "R48_BLIND_FOUR_WAY_20.jsonl"
    blind_path.write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in blind_rows),
        encoding="utf-8",
    )
    key_path = private_dir / "R48_PRIVATE_ANSWER_KEY.json"
    with key_path.open("x", encoding="utf-8") as stream:
        json.dump({
            "schema": "storyforge-r48-gold-four-arm-v1",
            "scope": "RETROSPECTIVE_EXPOSED_V01_TEST",
            "items": answer_key,
        }, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    os.chmod(key_path, 0o600)
    result = {
        "status": "R48_GOLD_PLUS_THREE_MODEL_20_80_BLIND_PACK_PASS_NO_PROMOTION",
        "sample_count": 20, "reply_count": 80,
        "frozen_r47_run_key": RUN_KEY,
        "old_test_exposed": True,
        "no_gpu": True, "no_new_model_inference": True,
        "no_training": True, "no_gold_absolute_truth_assumption": True,
        "no_model_quality_promotion": True,
        "source_compiled_test_sha256": sha(compiled_test),
        "original_gold_target_sha256": [
            hashlib.sha256(s.encode("utf-8")).hexdigest() for s in original
        ],
        "input_sha256": {
            "prompt": sha(prompts_file),
            "manifest": sha(manifest_file),
            "r47_report": sha(report_file),
            **{arm: sha(model_files[arm]) for arm in ("base", "v01", "v02")},
        },
        "reviewer_sha256": {
            f"R48_Reviewer_{i:02d}.csv": sha(review_dir / f"R48_Reviewer_{i:02d}.csv")
            for i in (1, 2, 3)
        },
        "blind_sha256": sha(blind_path),
        "private_key_sha256": sha(key_path),
    }
    (output / "coordinator" / "R48_PRIVATE_SOURCE_AUDIT.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return result


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--compiled-test", type=Path, required=True)
    p.add_argument("--prompts", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--r47-coordinator", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()
    result = build(
        compiled_test=args.compiled_test,
        prompts_file=args.prompts,
        manifest_file=args.manifest,
        report_file=args.r47_coordinator / "R47_PRIVATE_RUN_REPORT.json",
        model_files={
            name: args.r47_coordinator / f"{name}-results.jsonl"
            for name in ("base", "v01", "v02")
        },
        output=args.out_dir,
    )
    print(result["status"])
    print("R48_REVIEWER_DIR=" + str(args.out_dir / "reviewers"))
    print("R48_PRIVATE_KEY_DIR=" + str(args.out_dir / "coordinator" / "private"))


if __name__ == "__main__":
    main()
