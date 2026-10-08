"""Dedicated StoryForge rank-64 capacity and baseline entrypoint (never smoke)."""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from importlib.metadata import version
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.hf_job_runner import (
    GpuMonitor,
    Runner,
    check_inference_result,
    collect_environment,
    count_rows,
    make_inference_input,
    sha256,
    training_evidence,
)

ROOT = Path("/workspace")
CONFIG = ROOT / "configs/qwen38-27b-qlora-v0.1.yaml"
DATA = ROOT / "datasets/v0.3"


def build_train_command(run_dir: Path, *, mode: str) -> list[str]:
    if mode not in {"capacity", "baseline"}:
        raise ValueError(f"invalid mode: {mode}")
    cmd = [
        "swift", "sft", str(CONFIG),
        "--dataset", str(run_dir / "train.jsonl"),
        "--val_dataset", str(run_dir / "validation.jsonl"),
        "--output_dir", str(run_dir / "output"),
        "--save_only_model", "false",
        "--loss_scale", "last_round",
        "--custom_register_path", str(ROOT / "scripts/hf_smoke_guard.py"),
    ]
    if mode == "capacity":
        # One real optimizer step at rank 64, not a full epoch.
        cmd += ["--max_steps", "1", "--save_strategy", "steps", "--save_steps", "1",
                "--eval_strategy", "no"]
    return cmd


def validate_config() -> None:
    import yaml

    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    required = {
        "model": "Qwen/Qwen3.8-27B", "lora_rank": 64, "lora_alpha": 128,
        "max_length": 16384, "loss_scale": "last_round",
        "disable_ignore_empty_think": True, "add_non_thinking_prefix": False,
        "num_train_epochs": 1, "gradient_accumulation_steps": 8,
        "eval_steps": 3, "save_steps": 3,
    }
    for key, expected in required.items():
        if config.get(key) != expected:
            raise ValueError(f"baseline config {key}: expected {expected!r}, got {config.get(key)!r}")
    if "max_steps" in config:
        raise ValueError("full-epoch baseline must not contain max_steps")
    if config.get("eval_strategy") != "steps" or config.get("save_strategy") != "steps":
        raise ValueError("baseline requires explicit step-based eval/save")
    if "test" in json.dumps(config.get("dataset", [])):
        raise ValueError("held-out test must not be in training data")


def validate_capacity_evidence(output: Path) -> int:
    states = list(output.rglob("trainer_state.json"))
    if not states:
        raise RuntimeError("capacity step has no trainer_state.json")
    state = max((json.loads(p.read_text(encoding="utf-8")) for p in states),
                key=lambda d: int(d.get("global_step", 0)))
    steps = int(state.get("global_step", 0))
    losses = [float(item["loss"]) for item in state.get("log_history", []) if item.get("loss") is not None]
    if steps != 1 or not losses or not all(math.isfinite(v) for v in losses):
        raise RuntimeError("capacity qualification requires exactly one step and finite loss")
    return steps


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("capacity", "baseline"), required=True)
    parser.add_argument("--git-commit", required=True)
    parser.add_argument("--capacity-job-id")
    args = parser.parse_args()
    job_id = os.environ.get("JOB_ID", "")
    if not job_id or not job_id.replace("-", "").isalnum():
        raise RuntimeError("missing or invalid JOB_ID")
    validate_config()
    if args.mode == "baseline":
        if not args.capacity_job_id or not args.capacity_job_id.replace("-", "").isalnum():
            raise RuntimeError("baseline requires --capacity-job-id from accepted rank-64 qualification")
        prior = ROOT / "baseline-runs" / "capacity" / args.capacity_job_id
        if not (prior / "CAPACITY_PASS").is_file():
            raise RuntimeError(f"capacity PASS is missing: {prior}")
        prior_summary = (prior / "summary.md").read_text(encoding="utf-8")
        if f"config_sha256: {sha256(CONFIG)}" not in prior_summary:
            raise RuntimeError("capacity config hash does not match baseline config")
    run_dir = ROOT / "baseline-runs" / args.mode / job_id
    run_dir.mkdir(parents=True, exist_ok=False)
    runner = Runner(run_dir)
    os.environ["CUDA_VISIBLE_DEVICES"] = "0"
    os.environ["HF_HOME"] = str(ROOT / "cache/huggingface")
    os.environ["PIP_CACHE_DIR"] = str(ROOT / "cache/pip")
    started = time.monotonic()
    status = "FAIL"
    evidence: dict[str, object] = {}
    peak = 0
    details = [f"mode: {args.mode}", f"git_commit: {args.git_commit}",
               "config: configs/qwen38-27b-qlora-v0.1.yaml"]
    try:
        collect_environment(runner, before=True, require_gpu=True)
        runner.run([sys.executable, "-m", "pip", "install", "-U",
                    "ms-swift==4.5.3", "transformers==5.16.1",
                    "bitsandbytes==0.50.2", "qwen-vl-utils==0.0.14"])
        (run_dir / "environment.json").write_text(json.dumps({
            "job_id": job_id, "mode": args.mode, "git_commit": args.git_commit,
            "packages": {name: version(name) for name in
                         ("ms-swift", "transformers", "bitsandbytes", "qwen_vl_utils")},
        }, indent=2), encoding="utf-8")
        for split in ("train", "validation"):
            source = DATA / f"{split}.jsonl"
            runner.run([sys.executable, str(ROOT / "scripts/prepare_sft.py"),
                        "--source", str(source), "--output", str(run_dir / f"{split}.jsonl")])
        runner.run([sys.executable, str(ROOT / "scripts/hf_cpu_preflight.py"),
                    "--data", str(run_dir), "--config", str(CONFIG)])
        for split in ("train", "validation"):
            file = run_dir / f"{split}.jsonl"
            runner.run([sys.executable, str(ROOT / "scripts/hf_label_mask_audit.py"),
                        "--dataset", str(file), "--model", "Qwen/Qwen3.8-27B",
                        "--samples", str(count_rows(file)), "--config", str(CONFIG)])
        details.append("preflight and label audits: PASS")
        with GpuMonitor() as monitor:
            code = runner.stream(build_train_command(run_dir, mode=args.mode))
        peak = monitor.peak_mib
        if code:
            raise RuntimeError(f"swift sft exit code {code}")
        if args.mode == "capacity":
            step = validate_capacity_evidence(run_dir / "output")
            if peak <= 0 or peak >= 77000:
                raise RuntimeError(f"rank-64 GPU capacity peak {peak} MiB is outside 0..77000 safety band")
            evidence = {"training_steps": step, "peak_vram_mib": peak}
            (run_dir / "CAPACITY_PASS").write_text("rank-64 single-step capacity verified\n", encoding="utf-8")
        else:
            evidence = training_evidence(run_dir / "output")
            if int(evidence["global_step"]) < 8:
                raise RuntimeError("baseline completed fewer than 8 optimizer steps")
            adapter = Path(str(evidence["adapter"]))
            prompt = run_dir / "infer-input.jsonl"
            result = run_dir / "inference-results.jsonl"
            make_inference_input(run_dir / "validation.jsonl", prompt)
            runner.run(["swift", "infer", "--model", "Qwen/Qwen3.8-27B",
                        "--use_hf", "true", "--adapters", str(adapter),
                        "--val_dataset", str(prompt), "--val_dataset_sample", "1",
                        "--infer_backend", "transformers", "--torch_dtype", "bfloat16",
                        "--quant_method", "bnb", "--quant_bits", "4",
                        "--bnb_4bit_compute_dtype", "bfloat16",
                        "--max_new_tokens", "128", "--result_path", str(result)])
            check_inference_result(result)
            (run_dir / "BASELINE_PASS").write_text("one-epoch baseline and adapter inference verified\n",
                                                   encoding="utf-8")
        status = "PASS"
    except Exception as exc:
        details.append(f"error: {type(exc).__name__}: {exc}")
        raise
    finally:
        details += [f"peak_vram_mib: {peak}", f"evidence: {json.dumps(evidence, default=str)}",
                    f"config_sha256: {sha256(CONFIG)}",
                    f"elapsed_seconds: {time.monotonic() - started:.1f}",
                    f"status: {status}"]
        (run_dir / "summary.md").write_text(status + "\n" + "\n".join(details) + "\n",
                                            encoding="utf-8")
        runner.close()
        print("Artifacts at", run_dir, flush=True)


if __name__ == "__main__":
    main()
