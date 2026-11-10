"""R60 P3 CPU-only tokenizer/template/budget preflight; no weights or inference."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
from importlib.metadata import version
from pathlib import Path

MODEL_PINS = {
    "A": ("Qwen/Qwen3-32B", "9216db5781bf21249d130ec9da846c4624c16137"),
    "B": ("zai-org/GLM-4-32B-0414", "8dea913c41b543527c2860fb6f3c15c202f24aeb"),
    "challenger": ("zai-org/GLM-Z1-32B-0414", "8eb2858992c1f749e2a6d4075455decc2484722d"),
}
MODEL_FILES = {
    "A": ("config.json", "generation_config.json", "merges.txt", "tokenizer.json", "tokenizer_config.json", "vocab.json"),
    "B": ("chat_template.jinja", "config.json", "generation_config.json", "special_tokens_map.json", "tokenizer.json", "tokenizer_config.json"),
    "challenger": ("chat_template.jinja", "config.json", "generation_config.json", "special_tokens_map.json", "tokenizer.json", "tokenizer_config.json"),
}
WEIGHT_SUFFIXES = {".safetensors", ".bin", ".pt", ".pth", ".gguf", ".onnx", ".h5"}
RUBRIC_VERSION = "r60_severity_rubric_v2_1"
CONTEXT_CEILING = 32768
DEFAULT_OUTPUT_BUDGET = 4096
DEFAULT_INPUT_BUDGET = CONTEXT_CEILING - DEFAULT_OUTPUT_BUDGET
SYNTHETIC_CASES = 90


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def budget_fits(prompt_tokens: int, output_tokens: int, context_ceiling: int) -> bool:
    return (
        type(prompt_tokens) is int and prompt_tokens >= 0
        and type(output_tokens) is int and output_tokens >= 0
        and type(context_ceiling) is int and context_ceiling > 0
        and prompt_tokens + output_tokens <= context_ceiling
    )


def percentile95(values: list[int]) -> int:
    ordered = sorted(values)
    return ordered[max(0, (95 * len(ordered) + 99) // 100 - 1)]


def synthetic_messages(index: int, rubric_text: str) -> list[dict]:
    history = (
        f"<think>PRIVATE_SYNTHETIC_REASONING_{index}</think>"
        f"VISIBLE_SYNTHETIC_HISTORY_{index}：NPC 主动提出一个虚构方案。"
    )
    return [
        {"role": "system", "content": rubric_text},
        {"role": "user", "content": f"合成测试第 {index} 轮：请审核虚构互动，不要续写。"},
        {"role": "assistant", "content": history, "meta": "analysis"},
        {"role": "user", "content": f"合成追问 {index}：区分玩家自主权、规则冲突和安全上下文。"},
    ]


def _render(tokenizer, messages: list[dict], *, role: str, template: str | None = None) -> str:
    original = tokenizer.chat_template
    try:
        if template is not None:
            tokenizer.chat_template = template
        kwargs = {"tokenize": False, "add_generation_prompt": True}
        if role == "A":
            kwargs["enable_thinking"] = True
        rendered = tokenizer.apply_chat_template(messages, **kwargs)
        if not isinstance(rendered, str) or not rendered:
            raise ValueError("P3_CHAT_TEMPLATE_RENDER_INVALID")
        return rendered
    finally:
        tokenizer.chat_template = original


def _verify_download_safe(path: Path, snapshots_root: Path) -> dict:
    safe = json.loads(path.read_text(encoding="utf-8"))
    if safe.get("schema") != "storyforge_r60_p3_model_files_safe_v1" or safe.get("status") != "P3_PINNED_TOKENIZER_FILES_READY__NO_WEIGHTS":
        raise ValueError("P3_DOWNLOAD_SAFE_SCHEMA_HOLD")
    if safe.get("model_count") != 3 or safe.get("model_weights_downloaded") is not False:
        raise ValueError("P3_DOWNLOAD_SAFE_MODEL_COUNT_HOLD")
    models = safe.get("models")
    if not isinstance(models, dict) or set(models) != set(MODEL_PINS):
        raise ValueError("P3_DOWNLOAD_SAFE_MODEL_SET_HOLD")
    for role, (model, revision) in MODEL_PINS.items():
        item = models[role]
        if (item.get("model"), item.get("revision")) != (model, revision):
            raise ValueError("P3_DOWNLOAD_SAFE_REVISION_HOLD")
        folder = snapshots_root / role / revision
        if not folder.is_dir() or folder.is_symlink():
            raise ValueError("P3_LOCAL_SNAPSHOT_MISSING_HOLD")
        recorded = item.get("files")
        if not isinstance(recorded, dict) or set(recorded) != set(MODEL_FILES[role]):
            raise ValueError("P3_DOWNLOAD_SAFE_FILE_SET_HOLD")
        for name in MODEL_FILES[role]:
            file_path = folder / name
            if not file_path.is_file() or file_path.is_symlink():
                raise ValueError("P3_REQUIRED_MODEL_FILE_MISSING_HOLD")
            if sha256_file(file_path) != recorded[name].get("sha256"):
                raise ValueError("P3_LOCAL_FILE_HASH_MISMATCH_HOLD")
            if file_path.stat().st_size != recorded[name].get("bytes"):
                raise ValueError("P3_LOCAL_FILE_SIZE_MISMATCH_HOLD")
        for candidate in folder.rglob("*"):
            if candidate.is_file() and candidate.suffix.lower() in WEIGHT_SUFFIXES:
                raise ValueError("P3_MODEL_WEIGHT_DETECTED_HOLD")
    return safe


def preflight(
    profiles_path: Path,
    snapshots_root: Path,
    download_safe_path: Path,
    *,
    input_budget: int = DEFAULT_INPUT_BUDGET,
    output_budget: int = DEFAULT_OUTPUT_BUDGET,
    context_ceiling: int = CONTEXT_CEILING,
) -> dict:
    import jinja2
    import sentencepiece
    import transformers
    from storyforge_gold_quality import hf_severity_evidence_v2 as severity

    baseline = {"transformers": "4.57.1", "sentencepiece": "0.2.1", "jinja2": "3.1.6"}
    installed = {name: version(name) for name in baseline}
    if installed != baseline:
        raise ValueError("P3_RUNTIME_DEPENDENCY_PIN_HOLD")
    if context_ceiling != CONTEXT_CEILING or not budget_fits(input_budget, output_budget, context_ceiling):
        raise ValueError("P3_SHARED_CONTEXT_BUDGET_HOLD")
    if input_budget < 1024 or output_budget < 1:
        raise ValueError("P3_SHARED_CONTEXT_BUDGET_HOLD")

    download_safe = _verify_download_safe(download_safe_path, snapshots_root)
    profiles = json.loads(profiles_path.read_text(encoding="utf-8"))
    model_profiles = profiles.get("model_profiles")
    if (profiles.get("schema") != "storyforge_r60_p3_model_profiles_v1"
            or profiles.get("rubric_version") != severity.RUBRIC_VERSION
            or not isinstance(model_profiles, dict)
            or set(model_profiles) != set(MODEL_PINS)):
        raise ValueError("P3_PROFILE_SCHEMA_HOLD")

    results = {}
    template_mismatch_roles = []
    for role, (expected_model, expected_revision) in MODEL_PINS.items():
        profile = model_profiles[role]
        if (profile.get("model"), profile.get("revision")) != (expected_model, expected_revision):
            raise ValueError("P3_MODEL_REVISION_HOLD")
        if role == "A" and (
            profile.get("enable_thinking") is not True
            or profile.get("sampling") != {
                "do_sample": True, "temperature": 0.6, "top_p": 0.95,
                "top_k": 20, "min_p": 0,
            }
        ):
            raise ValueError("P3_QWEN_THINKING_PROFILE_HOLD")

        folder = snapshots_root / role / expected_revision
        tokenizer = transformers.AutoTokenizer.from_pretrained(
            str(folder), local_files_only=True, trust_remote_code=False
        )
        embedded = tokenizer.chat_template
        if not isinstance(embedded, str) or not embedded.strip():
            raise ValueError("P3_CHAT_TEMPLATE_MISSING_HOLD")
        embedded_sha = hashlib.sha256(embedded.encode("utf-8")).hexdigest()

        standalone_path = folder / "chat_template.jinja"
        standalone = standalone_path.read_text(encoding="utf-8") if standalone_path.exists() else None
        standalone_sha = hashlib.sha256(standalone.encode("utf-8")).hexdigest() if standalone else None
        embedded_standalone_mismatches = 0
        embedded_prefixes = []
        standalone_prefixes = []
        token_lengths = []
        for index in range(SYNTHETIC_CASES):
            messages = synthetic_messages(index, severity.RUBRIC_TEXT)
            rendered = _render(tokenizer, messages, role=role)
            embedded_prefixes.append(rendered[-96:])
            ids = tokenizer.apply_chat_template(
                messages, tokenize=True, add_generation_prompt=True,
                **({"enable_thinking": True} if role == "A" else {}),
            )
            if not isinstance(ids, list) or not ids or any(type(token) is not int for token in ids):
                raise ValueError("P3_TOKEN_IDS_INVALID_HOLD")
            token_lengths.append(len(ids))
            if len(ids) > input_budget:
                raise ValueError("P3_SYNTHETIC_INPUT_BUDGET_HOLD")
            if standalone is not None:
                alternate = _render(tokenizer, messages, role=role, template=standalone)
                standalone_prefixes.append(alternate[-96:])
                if rendered != alternate:
                    embedded_standalone_mismatches += 1

        if role == "challenger":
            if any(f"PRIVATE_SYNTHETIC_REASONING_{i}" in _render(
                tokenizer, synthetic_messages(i, severity.RUBRIC_TEXT), role=role
            ) for i in range(SYNTHETIC_CASES)):
                raise ValueError("P3_GLMZ1_HISTORY_THINK_LEAK_HOLD")
            if any(f"VISIBLE_SYNTHETIC_HISTORY_{i}" not in _render(
                tokenizer, synthetic_messages(i, severity.RUBRIC_TEXT), role=role
            ) for i in range(SYNTHETIC_CASES)):
                raise ValueError("P3_GLMZ1_HISTORY_CONTENT_MISSING_HOLD")

        if embedded_standalone_mismatches:
            template_mismatch_roles.append(role)
        results[role] = {
            "model": expected_model,
            "revision": expected_revision,
            "tokenizer_class": tokenizer.__class__.__name__,
            "embedded_template_sha256": embedded_sha,
            "standalone_template_sha256": standalone_sha,
            "embedded_standalone_render_mismatches": embedded_standalone_mismatches,
            "synthetic_inputs_checked": len(token_lengths),
            "prompt_tokens": {
                "min": min(token_lengths),
                "median": int(statistics.median(token_lengths)),
                "p95": percentile95(token_lengths),
                "max": max(token_lengths),
            },
            "generation_prompt_suffix_examples": {
                "embedded": embedded_prefixes[0],
                "standalone": standalone_prefixes[0] if standalone_prefixes else None,
            },
        }

    schema = severity.response_schema_v2()
    if schema.get("required") != ["schema", "rubric_version", "case_ref", "assessments"]:
        raise ValueError("P3_OUTPUT_SCHEMA_CONTRACT_HOLD")
    if set(schema["properties"]["assessments"]["required"]) != {"player_agency", "hard_rule", "safety"}:
        raise ValueError("P3_OUTPUT_SCHEMA_DIMENSIONS_HOLD")

    status = (
        "P3_TEMPLATE_SOURCE_DECISION_REQUIRED_HOLD"
        if template_mismatch_roles
        else "P3_SYNTHETIC_CPU_PREFLIGHT_PASS__GENERATION_PROFILE_PENDING"
    )
    return {
        "schema": "storyforge_r60_p3_cpu_preflight_safe_v2",
        "status": status,
        "model_count": 3,
        "models": results,
        "template_source_decision_required": template_mismatch_roles,
        "runtime_versions": {
            **installed,
            "tokenizers": version("tokenizers"),
            "huggingface-hub": version("huggingface-hub"),
        },
        "context_ceiling_tokens": context_ceiling,
        "input_budget_tokens": input_budget,
        "reserved_output_tokens": output_budget,
        "budget_sum_tokens": input_budget + output_budget,
        "synthetic_inputs_per_model": SYNTHETIC_CASES,
        "truncation_policy": "NO_TRUNCATION__REJECT_OVER_BUDGET",
        "rubric_version": severity.RUBRIC_VERSION,
        "rubric_sha256": hashlib.sha256(severity.RUBRIC_TEXT.encode("utf-8")).hexdigest(),
        "response_schema_sha256": hashlib.sha256(
            json.dumps(schema, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "finish_reason_runtime_validation": "DEFERRED_TO_P4_NO_INFERENCE_IN_P3",
        "private_case_tokens_checked": 0,
        "inference_calls": 0,
        "model_weights_loaded": False,
        "hf_jobs_submitted": 0,
        "gpu_started": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "profile_freeze_authorized": False,
        "private_values_emitted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiles", type=Path, default=Path(
        "experiments/r60_quality/p3_model_profiles_candidate_v1.json"))
    parser.add_argument("--snapshots-root", required=True, type=Path)
    parser.add_argument("--download-safe", required=True, type=Path)
    parser.add_argument("--input-budget", type=int, default=DEFAULT_INPUT_BUDGET)
    parser.add_argument("--output-budget", type=int, default=DEFAULT_OUTPUT_BUDGET)
    parser.add_argument("--context-ceiling", type=int, default=CONTEXT_CEILING)
    args = parser.parse_args()
    try:
        result = preflight(
            args.profiles, args.snapshots_root, args.download_safe,
            input_budget=args.input_budget, output_budget=args.output_budget,
            context_ceiling=args.context_ceiling,
        )
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 42 if result["status"].endswith("_HOLD") else 0
    except (ValueError, OSError, ImportError, TypeError, KeyError, RuntimeError) as exc:
        code = str(exc) if isinstance(exc, ValueError) and re.fullmatch(
            r"P3_[A-Z0-9_]+(?:_HOLD)?", str(exc)
        ) else "P3_CPU_PREFLIGHT_ERROR_HOLD"
        print(json.dumps({
            "schema": "storyforge_r60_p3_cpu_preflight_safe_v2",
            "status": "P3_CPU_PREFLIGHT_HOLD",
            "reason_code": code,
            "inference_calls": 0,
            "model_weights_loaded": False,
            "hf_jobs_submitted": 0,
            "gpu_started": False,
            "training_authorized": False,
            "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
