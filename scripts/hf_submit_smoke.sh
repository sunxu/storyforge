#!/usr/bin/env bash
set -euo pipefail
# Run locally with hf CLI authenticated; no GPU is provisioned until the final command.
cd "$(dirname "$0")/.."
BUCKET="hf://buckets/adradar/storyforge-training"
test -s data/compiled/v0.3/train.jsonl
test -s data/compiled/v0.3/validation.jsonl
hf buckets sync data/compiled/v0.3 "$BUCKET/datasets/v0.3"
hf buckets cp scripts/hf_job_runner.py "$BUCKET/scripts/hf_job_runner.py"
hf buckets cp scripts/prepare_sft.py "$BUCKET/scripts/prepare_sft.py"
hf buckets cp scripts/hf_cpu_preflight.py "$BUCKET/scripts/hf_cpu_preflight.py"
hf buckets cp configs/qwen38-27b-qlora-smoke.yaml "$BUCKET/configs/qwen38-27b-qlora-smoke.yaml"
echo "Files synced to $BUCKET"
if [[ "${1:-}" != "--submit" ]]; then
  echo "DRY RUN: no GPU requested. To submit a billable 45m A100 job: $0 --submit"
  exit 0
fi
hf jobs run --namespace adradar --name storyforge-qlora-smoke \
  --flavor a100-large --timeout 45m \
  -v "$BUCKET:/workspace:rw" \
  pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime \
  python /workspace/scripts/hf_job_runner.py
