"""Two-arm validation inference for StoryForge; never trains or reads held-out test."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.hf_job_runner import Runner, check_inference_result, sha256
from scripts.prepare_eval_pairs import prepare_pairs

ROOT = Path("/workspace")
PROMPTS = ROOT / "evaluation/v0.1/validation-prompts.jsonl"
MANIFEST = ROOT / "evaluation/v0.1/validation-manifest.json"
ADAPTER = (ROOT / "baseline-runs/baseline/6ac75bafdf2184ac91acb293/"
           "output/v0-20261008-090236/checkpoint-9")
MODEL = "Qwen/Qwen3.8-27B"


def infer_command(result: Path, *, adapter: bool) -> list[str]:
    cmd = ["swift", "infer", "--model", MODEL, "--use_hf", "true"]
    if adapter:
        cmd.extend(["--adapters", str(ADAPTER)])
    return cmd + [
        "--val_dataset", str(PROMPTS),
        "--infer_backend", "transformers", "--torch_dtype", "bfloat16",
        "--quant_method", "bnb", "--quant_bits", "4",
        "--bnb_4bit_compute_dtype", "bfloat16", "--max_new_tokens", "128",
        "--seed", "42", "--data_seed", "42", "--do_sample", "false",
        "--val_dataset_shuffle", "false", "--result_path", str(result),
    ]


def validate_input() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("schema") != "storyforge-blind-v1":
        raise ValueError("invalid manifest schema")
    rows = [json.loads(line) for line in PROMPTS.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    if len(rows) != manifest.get("count") or len(rows) != 15 or len(manifest["samples"]) != 15:
        raise ValueError("validation evaluation requires exactly 15 prompts")
    import hashlib
    for row, entry in zip(rows, manifest["samples"]):
        messages = row["messages"]
        if not messages or messages[-1]["role"] != "user":
            raise ValueError("prompt must end with user")
        if any("loss" in m for m in messages):
            raise ValueError("training loss metadata in inference prompt")
        normalized = json.dumps({"messages": messages}, sort_keys=True, ensure_ascii=False)
        if hashlib.sha256(normalized.encode("utf-8")).hexdigest() != entry["prompt_sha256"]:
            raise ValueError("prompt hash mismatch")
    if not (ADAPTER / "adapter_model.safetensors").is_file():
        raise FileNotFoundError(f"adapter missing: {ADAPTER}")
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--git-commit", required=True)
    args = parser.parse_args()
    job_id = os.environ.get("JOB_ID", "")
    if not job_id or not job_id.replace("-", "").isalnum():
        raise RuntimeError("missing invalid JOB_ID")
    run_dir = ROOT / "evaluation-runs/validation" / job_id
    run_dir.mkdir(parents=True, exist_ok=False)
    runner = Runner(run_dir)
    start = time.monotonic()
    status = "FAIL"
    details = [f"git_commit: {args.git_commit}", "split: validation",
               f"model: {MODEL}", f"adapter: {ADAPTER}"]
    try:
        runner.run([sys.executable, "-m", "pip", "install", "-U",
                    "ms-swift==4.5.3", "transformers==5.16.1",
                    "bitsandbytes==0.50.2", "qwen-vl-utils==0.0.14"])
        runner.run([sys.executable, str(ROOT / "scripts/hf_eval_cli_preflight.py")],
                   name="eval-cli-preflight.txt")
        count = validate_input()
        base = run_dir / "base-results.jsonl"
        tuned = run_dir / "adapter-results.jsonl"
        runner.run(infer_command(base, adapter=False), name="base-infer.log")
        check_inference_result(base)
        runner.run(infer_command(tuned, adapter=True), name="adapter-infer.log")
        check_inference_result(tuned)
        graded = run_dir / "blind-pairs.jsonl"
        private_key = run_dir / "PRIVATE-answer-key.json"
        prepare_pairs(MANIFEST, base, tuned, graded, private_key, PROMPTS)
        details.extend([f"pairs: {count}", f"manifest_sha256: {sha256(MANIFEST)}",
                        f"prompts_sha256: {sha256(PROMPTS)}", "paired_inference: PASS"])
        status = "PASS"
        (run_dir / "EVAL_GENERATION_PASS").write_text("paired generation validated\n", encoding="utf-8")
    except Exception as exc:
        details.append(f"error: {type(exc).__name__}: {exc}")
        raise
    finally:
        details.extend([f"elapsed_seconds: {time.monotonic() - start:.1f}",
                        f"status: {status}"])
        (run_dir / "summary.md").write_text(status + "\n" + "\n".join(details) + "\n",
                                            encoding="utf-8")
        runner.close()
        print("Artifacts at", run_dir, flush=True)


if __name__ == "__main__":
    main()
