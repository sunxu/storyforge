#!/usr/bin/env bash
# R60 GLM full-25 frozen evaluation with lossless private generation snapshots.
# Run only inside the digest-pinned vLLM H200 image; Owner launches HF Job.
set -euo pipefail
export TOKENIZERS_PARALLELISM=false
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

RUN_ID="${1:?RUN_ID_REQUIRED}"
if [[ ! "$RUN_ID" =~ ^r60-glm-full25-snapshot-[0-9]{8}T[0-9]{6}Z$ ]]; then
  echo FULL25_RUN_ID_HOLD
  exit 42
fi
test -f /input/runner.py
test -f /input/source.private.jsonl
test -f /input/r60_glm4_b25_continuous_review.py
test -f /input/r60_generation_snapshot.py
test -d /model-source

mkdir -p /bucket/evaluation-runs /bucket/private-generation-snapshots
OUTPUT="/bucket/evaluation-runs/$RUN_ID"
SNAP="/bucket/private-generation-snapshots/$RUN_ID"
if [[ -e "$OUTPUT" || -e "$SNAP" || -L "$OUTPUT" || -L "$SNAP" ]]; then
  echo FULL25_DESTINATION_EXISTS_HOLD
  exit 42
fi
umask 077
mkdir -m 700 "$OUTPUT"
mkdir -m 700 "$SNAP"

LOCAL="/tmp/$RUN_ID"
python3 -u /input/r60_glm4_servercopy_localize.py \
  --skip-weight-sha \
  --bucket-dir /model-source \
  --local-dir "$LOCAL"

export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
exec python3 -u /input/r60_glm4_b25_continuous_review.py \
  --input /input/source.private.jsonl \
  --output-dir "$OUTPUT" \
  --generation-snapshot-dir "$SNAP" \
  --snapshot-full25 \
  --isolate-technical-failures \
  --model zai-org/GLM-4-32B-0414 \
  --revision 8dea913c41b543527c2860fb6f3c15c202f24aeb \
  --local-dir "$LOCAL" \
  --case-limit 25 \
  --batch-size 5 \
  --max-model-len 32768 \
  --max-output-tokens 2400 \
  --wall-seconds 5400 \
  --confirm-paid-gpu
