#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
BUCKET="hf://buckets/adradar/storyforge-training"
MODE="${1:-sync}"
case "$MODE" in sync|capacity|baseline) ;; *) echo "Usage: $0 [sync|capacity|baseline CAPACITY_JOB_ID]" >&2; exit 2;; esac
if [[ "$MODE" == baseline && -z "${2:-}" ]]; then
  echo "baseline requires a successful capacity job ID" >&2
  exit 2
fi
test -s data/compiled/v0.3/train.jsonl
test -s data/compiled/v0.3/validation.jsonl
if [[ "$MODE" != sync && "${STORYFORGE_ALLOW_PAID_GPU:-}" != "YES" ]]; then
  echo "REFUSED: set STORYFORGE_ALLOW_PAID_GPU=YES for paid GPU job" >&2
  exit 2
fi
for file in \
  data/compiled/v0.3/train.jsonl \
  data/compiled/v0.3/validation.jsonl \
  scripts/hf_baseline_runner.py \
  scripts/hf_job_runner.py \
  scripts/hf_smoke_guard.py \
  scripts/prepare_sft.py \
  scripts/hf_cpu_preflight.py \
  scripts/hf_label_mask_audit.py \
  configs/qwen38-27b-qlora-v0.1.yaml; do
  destination="$file"
  if [[ "$file" == data/compiled/* ]]; then destination="${file/data\/compiled/datasets}"; fi
  hf buckets cp "$file" "$BUCKET/$destination"
done
echo "Synced baseline files (no GPU yet)"
if [[ "$MODE" == sync ]]; then
  echo "SYNC PASS: no GPU launched"
  exit 0
fi
if [[ "$MODE" == capacity ]]; then
  hf jobs run --namespace adradar --name storyforge-rank64-capacity \
    --flavor a100-large --timeout 45m -v "$BUCKET:/workspace:rw" \
    pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime \
    python /workspace/scripts/hf_baseline_runner.py --mode capacity --git-commit "$(git rev-parse HEAD)"
else
  hf jobs run --namespace adradar --name storyforge-baseline-v01 \
    --flavor a100-large --timeout 120m -v "$BUCKET:/workspace:rw" \
    pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime \
    python /workspace/scripts/hf_baseline_runner.py --mode baseline \
    --capacity-job-id "$2" --git-commit "$(git rev-parse HEAD)"
fi
