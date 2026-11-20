#!/usr/bin/env bash
# HF CPU-only, pinned Qwen tokenizer dependencies; no CUDA, model weights or retries.
set -euo pipefail
umask 077
export CUDA_VISIBLE_DEVICES=""
export NVIDIA_VISIBLE_DEVICES="void"
export TOKENIZERS_PARALLELISM=false
export HF_HUB_DISABLE_TELEMETRY=1

STAGE=/input/gold48
RUN_KEY="${1:-}"
[[ "$RUN_KEY" =~ ^r60-gold48-cpu-[0-9]{8}T[0-9]{6}Z-[a-f0-9]{12}$ ]] || {
  echo "GOLD48_HF_CPU_RUN_KEY_HOLD"
  exit 42
}
test -f "$STAGE/private/GOLD48_HF_CPU_MINIMAL_INPUT_PRIVATE.json" || {
  echo "GOLD48_HF_CPU_PRIVATE_INPUT_MISSING_HOLD"
  exit 42
}
test -f "$STAGE/requirements/hf-cpu-tokenizer.lock" || {
  echo "GOLD48_HF_CPU_DEPENDENCY_LOCK_MISSING_HOLD"
  exit 42
}
# Suppress dependency manager output to avoid accidental logs of paths or values.
if ! python3 -m pip install --quiet --no-cache-dir --disable-pip-version-check \
  --require-hashes -r "$STAGE/requirements/hf-cpu-tokenizer.lock" >/dev/null 2>&1; then
  echo "GOLD48_HF_CPU_DEPENDENCY_INSTALL_HOLD"
  exit 42
fi
if ! python3 -m pip check >/dev/null 2>&1; then
  echo "GOLD48_HF_CPU_DEPENDENCY_INTEGRITY_HOLD"
  exit 42
fi
PYTHONPATH="$STAGE/src:$STAGE/scripts" \
  python3 "$STAGE/scripts/r60_p2_gold48_hf_cpu_worker.py" \
    --stage "$STAGE" --output /output --run-key "$RUN_KEY"
