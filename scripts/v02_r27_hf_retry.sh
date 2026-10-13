#!/usr/bin/env bash
# Retry R27 no-training CPU audit with corrected 117-row worker; sync only code, never overwrite source.
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "${STORYFORGE_ALLOW_PAID_CPU:-}" != YES ]]; then
  echo "R27 BLOCKED: set STORYFORGE_ALLOW_PAID_CPU=YES to authorize paid CPU diagnostic" >&2
  exit 3
fi
command -v hf >/dev/null || { echo "R27 BLOCKED: HF CLI not installed" >&2; exit 2; }
WORKER="scripts/v02_r27_hf_worker.sh"
test -s "$WORKER" || { echo "R27 BLOCKED: missing fixed worker" >&2; exit 2; }
EXPECTED="cdecc311f05e2c700f1038f3afca09c889ff681d4ef55dc18dc7426c9d14a92a"
PREFIX="hf://buckets/adradar/storyforge-training/preflight/v02-r27"
RUN_KEY="r27-fix-$(date -u +%Y%m%dT%H%M%SZ)-${RANDOM}"
# The original R27 submit script reuploads the buggy worker; DO NOT invoke it for this retry.
hf buckets cp "$WORKER" "$PREFIX/code/r27_hf_worker.sh"
printf 'R27_EXPECTED_INPUT_SHA=%s\nR27_RUN_KEY=%s\nR27_RESULTS=%s/results/%s/\n' \
  "$EXPECTED" "$RUN_KEY" "$PREFIX" "$RUN_KEY"
hf jobs run --namespace adradar --name storyforge-v02-r27-117-mask-fix \
  --flavor cpu-upgrade --timeout 120m \
  --env "STORYFORGE_R27_INPUT_SHA=$EXPECTED" \
  --env "STORYFORGE_R27_RUN_KEY=$RUN_KEY" \
  -v "hf://buckets/adradar/storyforge-training:/workspace:rw" \
  pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime \
  bash /workspace/preflight/v02-r27/code/r27_hf_worker.sh both
