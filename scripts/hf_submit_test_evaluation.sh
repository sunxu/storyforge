#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
MODE="${1:-sync}"
case "$MODE" in
  sync|submit) ;;
  *) echo "usage: $0 [sync|submit]" >&2; exit 2 ;;
esac
if [[ "$MODE" == submit && "${STORYFORGE_ALLOW_PAID_GPU:-}" != "YES" ]]; then
  echo "REFUSED: paid A100 needs STORYFORGE_ALLOW_PAID_GPU=YES" >&2
  exit 2
fi
BUCKET="hf://buckets/adradar/storyforge-training"
test -s /tmp/storyforge-test-prompts.jsonl
test -s /tmp/storyforge-test-manifest.json
python - <<'PY'
import json
from pathlib import Path
p = [json.loads(x) for x in Path("/tmp/storyforge-test-prompts.jsonl").read_text().splitlines() if x.strip()]
m = json.loads(Path("/tmp/storyforge-test-manifest.json").read_text())
assert len(p) == len(m["samples"]) == m["count"] == 20, "held-out count must be 20"
assert all(row["messages"][-1]["role"] == "user" for row in p)
assert all(all("loss" not in msg for msg in row["messages"]) for row in p)
print("TEST_PROMPT_GATE_PASS: 20")
PY
for source in \
  scripts/hf_test_evaluation_runner.py \
  scripts/hf_eval_cli_preflight.py \
  scripts/hf_evaluation_runner.py \
  scripts/hf_job_runner.py \
  scripts/prepare_eval_pairs.py; do
  hf buckets cp "$source" "$BUCKET/$source"
done
hf buckets cp /tmp/storyforge-test-prompts.jsonl \
  "$BUCKET/evaluation/v0.1/test-prompts.jsonl"
hf buckets cp /tmp/storyforge-test-manifest.json \
  "$BUCKET/evaluation/v0.1/test-manifest.json"
echo "TEST_SYNC_PASS: Gold-free test inputs and runner synced; no GPU launched yet"
if [[ "$MODE" == sync ]]; then exit 0; fi
hf jobs run --namespace adradar --name storyforge-heldout-test-v01 \
  --flavor a100-large --timeout 240m \
  -v "$BUCKET:/workspace:rw" \
  pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime \
  python /workspace/scripts/hf_test_evaluation_runner.py \
    --git-commit "$(git rev-parse HEAD)"
