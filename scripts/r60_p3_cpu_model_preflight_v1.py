"""R60 P3 CPU-only offline tokenizer/template preflight; never loads model weights."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from importlib.metadata import version
from pathlib import Path


def preflight(profiles_path: Path, snapshots_root: Path, *, input_budget: int):
    from storyforge_gold_quality import hf_severity_evidence_v2 as severity
    import jinja2
    import sentencepiece
    import transformers

    del jinja2, sentencepiece
    baseline = {
        "transformers": "4.57.1",
        "sentencepiece": "0.2.1",
        "jinja2": "3.1.6",
    }
    if any(version(pkg) != pin for pkg, pin in baseline.items()):
        raise ValueError("P3_RUNTIME_DEPENDENCY_PIN_HOLD")
    profiles = json.loads(profiles_path.read_text(encoding="utf-8"))
    models = profiles.get("model_profiles")
    if (profiles.get("schema") != "storyforge_r60_p3_model_profiles_v1"
            or profiles.get("rubric_version") != severity.RUBRIC_VERSION
            or not isinstance(models, dict) or set(models) != {"A", "B", "challenger"}
            or type(input_budget) is not int or input_budget < 1024):
        raise ValueError("P3_PROFILE_OR_BUDGET_HOLD")
    output = {}
    prompt = [{"role": "system", "content": severity.RUBRIC_TEXT},
              {"role": "user", "content": "合成测试：请严格按三维证据标准回答。"}]
    for role, obj in models.items():
        model = obj.get("model")
        revision = obj.get("revision")
        if (not isinstance(model, str)
                or not isinstance(revision, str)
                or re.fullmatch(r"[a-f0-9]{40}", revision) is None):
            raise ValueError("P3_MODEL_REVISION_HOLD")
        folder = snapshots_root / role / revision
        if not folder.is_dir() or folder.is_symlink():
            raise ValueError("P3_LOCAL_SNAPSHOT_MISSING_HOLD")
        # local_files_only prevents network access; no AutoModel weights or inference.
        tokenizer = transformers.AutoTokenizer.from_pretrained(
            str(folder), local_files_only=True, trust_remote_code=False
        )
        kwargs = {"tokenize": True, "add_generation_prompt": True}
        if role == "A":
            if (obj.get("enable_thinking") is not True
                    or obj.get("sampling") != {
                        "do_sample": True, "temperature": 0.6, "top_p": 0.95,
                        "top_k": 20, "min_p": 0
                    }):
                raise ValueError("P3_QWEN_THINKING_PROFILE_HOLD")
            kwargs["enable_thinking"] = True
        ids = tokenizer.apply_chat_template(prompt, **kwargs)
        if not isinstance(ids, list) or not 0 < len(ids) <= input_budget:
            raise ValueError("P3_TOKEN_BUDGET_OR_TEMPLATE_HOLD")
        template = tokenizer.chat_template
        if not isinstance(template, str) or not template.strip():
            raise ValueError("P3_CHAT_TEMPLATE_MISSING_HOLD")
        output[role] = {
            "model": model, "revision": revision, "synthetic_input_tokens": len(ids),
            "chat_template_sha256": hashlib.sha256(template.encode()).hexdigest(),
        }
    return {
        "schema": "storyforge_r60_p3_cpu_preflight_safe_v1",
        "status": "P3_SYNTHETIC_CPU_PREFLIGHT_PASS__PRIVATE_90_PENDING",
        "model_count": 3, "model_checks": output,
        "rubric_sha256": hashlib.sha256(severity.RUBRIC_TEXT.encode()).hexdigest(),
        "private_case_tokens_checked": 0,
        "inference_calls": 0, "hf_jobs_submitted": 0, "gpu_started": False,
        "training_authorized": False, "private_values_emitted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiles", type=Path,
                        default=Path("experiments/r60_quality/p3_model_profiles_candidate_v1.json"))
    parser.add_argument("--snapshots-root", required=True, type=Path)
    parser.add_argument("--input-budget", required=True, type=int)
    args = parser.parse_args()
    try:
        safe = preflight(args.profiles, args.snapshots_root, input_budget=args.input_budget)
        print(json.dumps(safe, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as exc:
        # Intentional SAFE error allowlist: no paths, private text or traceback.
        code = str(exc) if isinstance(exc, ValueError) and re.fullmatch(
            r"P3_[A-Z0-9_]+(?:_HOLD)?", str(exc)
        ) else "P3_CPU_PREFLIGHT_ERROR_HOLD"
        print(json.dumps({
            "schema": "storyforge_r60_p3_cpu_preflight_safe_v1",
            "status": "P3_CPU_PREFLIGHT_HOLD", "reason_code": code,
            "inference_calls": 0, "hf_jobs_submitted": 0,
            "gpu_started": False, "training_authorized": False,
            "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
