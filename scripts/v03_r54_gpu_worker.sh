#!/usr/bin/env bash
# R54 31/9 V2 single paid GPU pilot, never launch through sync or verify.
set -euo pipefail
: "${STORYFORGE_R54_RUN_KEY:?R54 RUN_KEY required}"
[[ "$STORYFORGE_R54_RUN_KEY" =~ ^r54-v2-[0-9]{8}T[0-9]{6}Z-[0-9]{6}$ ]] || { echo R54_INVALID_RUN_KEY >&2; exit 2; }
[[ "${STORYFORGE_R54_PAID_GPU_SCOPE:-}" == R54_31_9_V2_16STEP_ONE_EPOCH ]] || { echo R54_GPU_SCOPE_NOT_AUTHORIZED >&2; exit 3; }
ROOT="/workspace/preflight/v03-r54/gpu/runs/$STORYFORGE_R54_RUN_KEY"
cd "$ROOT"
# Immutable uploaded source + config + code verified BEFORE any pip/model download.
sha256sum --check --status SHA256SUMS.txt || { echo R54_GPU_STAGE_SHA_MISMATCH >&2; exit 2; }
python "$ROOT/code/v03_r54_gpu_readiness_v2.py" \
  --release-dir "$ROOT/private/release" \
  --cpu-report "$ROOT/private/R53_HF_CPU40_AUDIT_REPORT_PRIVATE.json" \
  --cpu-intake "$ROOT/private/R53_CPU40_OWNER_INTAKE_VERIFIED.json" \
  --config "$ROOT/config/r54.yaml" \
  --out "/tmp/r54_gpu_worker_preflight_${STORYFORGE_R54_RUN_KEY}.json"
export PYTHONUNBUFFERED=1
exec python -u "$ROOT/code/v03_r54_gpu_runner.py"
