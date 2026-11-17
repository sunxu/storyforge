#!/usr/bin/env bash
# R60 Base336 GPU worker launcher. Stage RO and results RW are separate HF volumes.
set -euo pipefail
umask 077

KEY="${STORYFORGE_R60_BASE336_GPU_RUN_KEY:-}"
SCOPE="${STORYFORGE_R60_BASE336_GPU_SCOPE:-}"
[[ "$KEY" =~ ^r60-base336-gpu-[0-9]{8}T[0-9]{6}Z-[a-f0-9]{12}$ ]] || {
  echo R60_BASE336_GPU_RUN_KEY_HOLD >&2
  exit 42
}
[[ "$SCOPE" == R60_BASE336_293_43_ONE_EPOCH_A10080GB ]] || {
  echo R60_BASE336_GPU_SCOPE_HOLD >&2
  exit 42
}
[[ -f /input/r60-base336/SHA256_MANIFEST_PRIVATE.json && -d /output ]] || {
  echo R60_BASE336_GPU_VOLUME_HOLD >&2
  exit 42
}

export PYTHONUNBUFFERED=1
export HF_HUB_DISABLE_TELEMETRY=1
export TOKENIZERS_PARALLELISM=false
export HF_HOME=/tmp/r60-base336-cache/huggingface
export PIP_CACHE_DIR=/tmp/r60-base336-cache/pip
mkdir -p "$HF_HOME" "$PIP_CACHE_DIR"
chmod 700 /tmp/r60-base336-cache "$HF_HOME" "$PIP_CACHE_DIR"

SCRATCH="$(mktemp -d /tmp/r60-base336-worker-XXXXXXXX)"
chmod 700 "$SCRATCH"
trap 'rm -rf "$SCRATCH"' EXIT

PYTHONPATH="/input/r60-base336/src:/input/r60-base336/scripts:/input/r60-base336/experiments/r58_quality"
export PYTHONPATH

# Stage, P0 proof, manifest and data hashes are verified before dependency
# installation, model download, CUDA use or training.
if ! python /input/r60-base336/scripts/r60_base336_gpu_worker.py \
  --action preflight --stage /input/r60-base336 --output /output --run-key "$KEY" \
  > "$SCRATCH/preflight.safe" 2> "$SCRATCH/preflight.private"; then
  echo R60_BASE336_GPU_STAGE_PREFLIGHT_HOLD >&2
  exit 42
fi
grep -q '"status": "BASE336_GPU_STAGE_VERIFIED__NO_GPU"' "$SCRATCH/preflight.safe" || {
  echo R60_BASE336_GPU_STAGE_PREFLIGHT_HOLD >&2
  exit 42
}

if ! python -m pip install --disable-pip-version-check -q \
  -r /input/r60-base336/requirements/r60-base336-gpu.in \
  > "$SCRATCH/pip.private" 2>&1; then
  echo R60_BASE336_GPU_DEPENDENCY_INSTALL_HOLD >&2
  exit 42
fi

if ! python /input/r60-base336/scripts/r60_base336_gpu_worker.py \
  --action train --stage /input/r60-base336 --output /output --run-key "$KEY" \
  > "$SCRATCH/train.safe" 2> "$SCRATCH/train.private"; then
  # Worker writes a private SAFE receipt before returning nonzero.
  if [[ -s "$SCRATCH/train.safe" ]]; then cat "$SCRATCH/train.safe"; else
    echo R60_BASE336_GPU_WORKER_HOLD >&2
  fi
  exit 42
fi
cat "$SCRATCH/train.safe"
