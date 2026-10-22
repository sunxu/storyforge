#!/usr/bin/env bash
# R50 preseal tokenizer DRAFT only. HF Jobs CPU worker. No training or inference.
set -euo pipefail
umask 077
: "${STORYFORGE_R50_RUN_KEY:?R50 run key required}"
[[ "$STORYFORGE_R50_RUN_KEY" =~ ^r50-cpu46-[0-9]{8}T[0-9]{6}Z-[0-9]{6}$ ]] || { echo R50_CPU46_HOLD__INVALID_RUN_KEY >&2; exit 2; }
[[ "${STORYFORGE_R50_CPU46_DRAFT_ONLY:-}" == YES ]] || { echo R50_CPU46_HOLD__DRAFT_SCOPE_NOT_AUTHORIZED >&2; exit 3; }
export CUDA_VISIBLE_DEVICES=""
export TOKENIZERS_PARALLELISM=false
export PYTHONUNBUFFERED=1
export PIP_DISABLE_PIP_VERSION_CHECK=1
ROOT="/workspace/preflight/r50/cpu46/runs/$STORYFORGE_R50_RUN_KEY"
RESULT="/workspace/preflight/r50/cpu46/results/$STORYFORGE_R50_RUN_KEY"
[[ -f "$ROOT/SHA256SUMS.txt" ]] || { echo R50_CPU46_HOLD__MANIFEST_MISSING >&2; exit 2; }
python "$ROOT/code/v03_r50_hf_cpu46_audit.py" check-stage --stage "$ROOT"
# On CPU-only hardware, install only dependencies needed for real tokenizer execution.
# No ms-swift, no model weights, no torch, no GPU.
python -m pip install --quiet --disable-pip-version-check \
  'transformers==5.16.1' 'huggingface_hub>=1.7,<3' 'jinja2>=3.1,<4'
python -u "$ROOT/code/v03_r50_hf_cpu46_audit.py" run \
  --stage "$ROOT" --run-key "$STORYFORGE_R50_RUN_KEY" --output-dir "$RESULT"
echo R50_CPU46_HF_WORKER_COMPLETED__NO_TRAIN_NO_INFERENCE_NO_FINAL_SEAL
