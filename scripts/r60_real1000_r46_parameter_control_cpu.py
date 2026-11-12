"""Static, stdlib-only R60 Real1000 vs R46-style SFT hyperparameter control.

Reads only public config files, never private data. Does not submit jobs or
authorize training. PASS means proposal is identical to the checked-in baseline
on explicitly frozen hyperparameters; it does NOT prove R46 runtime-equivalence
of system prompts, model templates, or dataset contents.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/r60_real1000_r46_controlled_sft_policy.json"
BASELINE = ROOT / "configs/qwen38-27b-qlora-v0.1.yaml"
SCHEMA = "storyforge_r60_r46_parameter_control_safe_v1"

EXPECTED_FIXED = {
    "tuner_type": "lora", "target_modules": "all-linear",
    "lora_rank": 64, "lora_alpha": 128, "lora_dropout": 0.05,
    "torch_dtype": "bfloat16", "quant_method": "bnb", "quant_bits": 4,
    "bnb_4bit_compute_dtype": "bfloat16", "bnb_4bit_quant_type": "nf4",
    "bnb_4bit_use_double_quant": True,
    "max_length": 16384, "loss_scale": "last_round",
    "disable_ignore_empty_think": True, "add_non_thinking_prefix": False,
    "per_device_train_batch_size": 1, "per_device_eval_batch_size": 1,
    "gradient_accumulation_steps": 8, "learning_rate": 0.00005,
    "num_train_epochs": 1, "warmup_ratio": 0.05,
    "gradient_checkpointing": True,
}

class Hold(ValueError):
    pass


def yaml_public_scalars(raw: str) -> dict:
    """Parse only unindented simple key: scalar lines; no YAML execution."""
    result = {}
    for line in raw.splitlines():
        if not line or line.lstrip().startswith("#") or line.startswith((" ", "\t", "-")):
            continue
        match = re.fullmatch(r"([a-z_][a-z_0-9]*):[ \t]*(.*)", line)
        if not match:
            raise Hold("REFERENCE_FORMAT_HOLD")
        key, rawval = match.groups()
        if key in result:
            raise Hold("DUPLICATE_REFERENCE_KEY_HOLD")
        rawval = rawval.split(" #", 1)[0].strip()
        if rawval == "true": value = True
        elif rawval == "false": value = False
        elif re.fullmatch(r"-?\d+", rawval): value = int(rawval)
        elif re.fullmatch(r"-?\d+\.\d+", rawval): value = float(rawval)
        else: value = rawval
        result[key] = value
    return result


def inspect(policy_file: Path = CONFIG, baseline_file: Path = BASELINE) -> dict:
    report = {
        "schema": SCHEMA, "status": "R60_R46_PARAMETER_CONTROL_HOLD",
        "reason_code": "UNVERIFIED", "hyperparameters_checked": 0,
        "hyperparameters_equal_to_baseline": False,
        "r46_runtime_template_equivalence_verified": False,
        "r46_system_prompt_equivalence_verified": False,
        "deployment_template_compatibility_verified": False,
        "r60_derived_input_approved": False,
        "semantic_world_isolation_verified": False,
        "train_admitted": 0, "gpu_started": False, "hf_jobs_submitted": 0,
        "database_accessed": False, "private_values_emitted": False,
    }
    try:
        raw = policy_file.read_bytes()
        if len(raw) > 12000 or len(raw) < 100:
            raise Hold("POLICY_SIZE_HOLD")
        policy = json.loads(raw)
        if (type(policy) is not dict
            or policy.get("schema") != "storyforge_r60_real1000_r46_controlled_sft_policy_v1"
            or policy.get("status") != "PROPOSED_NOT_ADMITTED_NO_GPU"
            or policy.get("source_baseline_config") != "configs/qwen38-27b-qlora-v0.1.yaml"
            or policy.get("model") != "Qwen/Qwen3.8-27B"
            or policy.get("model_revision") != "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0"
            or policy.get("runtime") != {"ms_swift": "4.5.3", "transformers": "5.16.1"}
            or policy.get("explicit_train_template_candidate") != "qwen3_8"
            or policy.get("system_policy") != "UNRESOLVED_R46_USES_GENERIC_SYSTEM_R60_INPUT_HAS_NO_SYSTEM"
            or policy.get("r46_actual_template_equivalence") != "UNVERIFIED"
            or policy.get("r60_derived_data_policy") != "OWNER_PENDING"
            or policy.get("deployment_template_compatibility") != "NOT_ESTABLISHED"
            or policy.get("semantic_protection_isolation") != "HOLD"
            or type(policy.get("train_admitted")) is not int or policy["train_admitted"] != 0
            or type(policy.get("quality_v1_admitted")) is not int or policy["quality_v1_admitted"] != 0
            or policy.get("gpu_authorized") is not False
            or policy.get("new_hf_jobs_authorized") is not False
            or policy.get("expected_only_experimental_variable") != "TRAINING_DATA_AFTER_MATCHING_SYSTEM_AND_TEMPLATE"
        ):
            raise Hold("POLICY_CONTRACT_HOLD")
        fixed = policy.get("frozen_hyperparameters")
        if type(fixed) is not dict or set(fixed) != set(EXPECTED_FIXED):
            raise Hold("HYPERPARAMETER_KEYS_HOLD")
        if any(type(fixed[k]) is not type(v) or fixed[k] != v for k,v in EXPECTED_FIXED.items()):
            raise Hold("HYPERPARAMETER_DRIFT_HOLD")
        reference = yaml_public_scalars(baseline_file.read_text(encoding="utf-8"))
        if any(k not in reference or type(reference[k]) is not type(v) or reference[k] != v
               for k,v in EXPECTED_FIXED.items()):
            raise Hold("REFERENCE_BASELINE_MISMATCH_HOLD")
        report.update(
            status="R60_R46_PROPOSED_HYPERPARAMETER_CONTROL_PASS__SYSTEM_TEMPLATE_ADMISSION_HOLD",
            reason_code="STATIC_BASELINE_MATCH_ONLY",
            hyperparameters_checked=len(EXPECTED_FIXED),
            hyperparameters_equal_to_baseline=True,
        )
    except Exception as e:
        allowed = {"POLICY_SIZE_HOLD","POLICY_CONTRACT_HOLD","HYPERPARAMETER_KEYS_HOLD",
                   "HYPERPARAMETER_DRIFT_HOLD","REFERENCE_BASELINE_MISMATCH_HOLD",
                   "REFERENCE_FORMAT_HOLD","DUPLICATE_REFERENCE_KEY_HOLD"}
        report["reason_code"] = str(e) if type(e) is Hold and str(e) in allowed else "INPUT_OR_RUNTIME_HOLD"
    return report


def main() -> int:
    a = argparse.ArgumentParser()
    a.add_argument("--policy", type=Path, default=CONFIG)
    a.add_argument("--baseline", type=Path, default=BASELINE)
    opts = a.parse_args()
    result = inspect(opts.policy, opts.baseline)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["hyperparameters_equal_to_baseline"] else 42


if __name__ == "__main__":
    raise SystemExit(main())
