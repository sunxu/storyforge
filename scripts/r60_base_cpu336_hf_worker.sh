#!/usr/bin/env bash
# R60 Base CPU336: pinned CPU image, private RO input + isolated RW SAFE output.
set -euo pipefail
umask 077
export CUDA_VISIBLE_DEVICES=""
export TOKENIZERS_PARALLELISM=false
export USE_HF=true
export PYTHONUNBUFFERED=1
KEY="${STORYFORGE_R60_WRAPCPU_KEY:?MISSING_RUN_KEY}"
ROOT=/input/common2
[[ -f "$ROOT/SHA256_MANIFEST_PRIVATE.json" ]] || {
  echo BASE_CPU336_STAGE_MISSING_HOLD >&2
  exit 42
}
python -m pip install --disable-pip-version-check -r "$ROOT/requirements/r60-common2-wrapped-cpu.in" >/dev/null
export PYTHONPATH="$ROOT/src:$ROOT/scripts:$ROOT/experiments/r58_quality"
python "$ROOT/scripts/r60_base_cpu336_hf_worker.py" \
  --stage "$ROOT" --output /output --run-key "$KEY"
