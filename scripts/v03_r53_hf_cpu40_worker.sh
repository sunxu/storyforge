#!/usr/bin/env bash
# StoryForge R53 CPU-only diagnostic worker: NO TRAINING, no R50, no GPU.
set -euo pipefail
: "${STORYFORGE_R53_RUN_KEY:?R53 run key required}"
[[ "$STORYFORGE_R53_RUN_KEY" =~ ^r53-cpu40-[0-9]{8}T[0-9]{6}Z-[0-9]{6}$ ]] || {
  echo R53_RUN_KEY_INVALID >&2; exit 2;
}
ROOT="/workspace/preflight/v03-r53/cpu40/runs/$STORYFORGE_R53_RUN_KEY"
CODE="$ROOT/code"
STAGE="$ROOT/private_stage"
RESULT="/workspace/preflight/v03-r53/cpu40/results/$STORYFORGE_R53_RUN_KEY"
cd "$ROOT"
# Exact originally synced code and private file hashes verified before any pip install.
sha256sum --check --status SHA256SUMS.txt || { echo R53_UPLOADED_BUNDLE_SHA_MISMATCH >&2; exit 2; }
python "$CODE/v03_r53_hf_cpu40_audit.py" preflight --stage "$STAGE"
# A CPU-only job is billable, and the source gate above must run before pip.
export CUDA_VISIBLE_DEVICES=""
export HF_HOME="/workspace/cache/huggingface"
export TOKENIZERS_PARALLELISM=false
export PYTHONUNBUFFERED=1
python -m pip install --disable-pip-version-check \
  'ms-swift==4.5.3' 'transformers==5.16.1' \
  'huggingface_hub>=0.35,<3' 'qwen-vl-utils>=0.0.14'
mkdir -p "$RESULT"
cd "$CODE"  # Makes the official pinned hf_label_mask_audit.py importable.
python -u "$CODE/v03_r53_hf_cpu40_audit.py" audit \
  --stage "$STAGE" --output-dir "$RESULT/audit" 2>&1 | tee "$RESULT/R53_CPU40_RUNTIME_LOG_PRIVATE.txt"
# The final marker is only printed on genuine 40/40 actual runtime PASS.
sha256sum "$RESULT/R53_CPU40_RUNTIME_LOG_PRIVATE.txt" > "$RESULT/R53_CPU40_RUNTIME_LOG_SHA256SUMS.txt"
echo R53_HF_CPU40_WORKER_EXECUTED_NO_TRAIN
