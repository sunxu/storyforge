#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
BUCKET="hf://buckets/adradar/storyforge-training"
MODE="${1:-sync}"
case "$MODE" in
  sync|submit) ;;
  *) echo "usage: $0 [sync|submit]" >&2; exit 2 ;;
esac
if [[ "$MODE" == submit && "${STORYFORGE_ALLOW_PAID_GPU:-}" != "YES" ]]; then
  echo "REFUSED: paid evaluation requires STORYFORGE_ALLOW_PAID_GPU=YES" >&2
  exit 2
fi
test -s /tmp/storyforge-blind-validation.jsonl
test -s /tmp/storyforge-blind-validation-manifest.json
for src in \
  scripts/hf_evaluation_runner.py \
  scripts/hf_eval_cli_preflight.py \
  scripts/hf_job_runner.py \
  scripts/prepare_eval_pairs.py; do
  hf buckets cp "$src" "$BUCKET/$src"
done
hf buckets cp /tmp/storyforge-blind-validation.jsonl \
  "$BUCKET/evaluation/v0.1/validation-prompts.jsonl"
hf buckets cp /tmp/storyforge-blind-validation-manifest.json \
  "$BUCKET/evaluation/v0.1/validation-manifest.json"
echo "Evaluation scripts and Gold-free validation prompts synced."
if [[ "$MODE" == sync ]]; then
  echo "EVAL_SYNC_PASS: no GPU launched"
  exit 0
fi
hf jobs run --namespace adradar --name storyforge-blind-validation-v01 \
  --flavor a100-large --timeout 120m \
  -v "$BUCKET:/workspace:rw" \
  pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime \
  python /workspace/scripts/hf_evaluation_runner.py --git-commit "$(git rev-parse HEAD)"
