#!/usr/bin/env bash
# Gold48 thin HF Job launcher: frozen RO Stage -> exact hash-lock install -> existing Worker.
# No submitter, training code, authorization signer or extra Provider mount.
set -euo pipefail
umask 077

ACTION="${1:-}"
RUN_ID="${2:-}"
ROLE="${3:-}"
ENTRY=/input/code/scripts/r60_gold48_gpu_worker_entry.py
LOCK=/input/gold48/runtime_lock.hashes

[[ "$ACTION" == check || "$ACTION" == execute ]] || {
  echo GOLD48_ACTION_HOLD >&2
  exit 42
}
[[ "$RUN_ID" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{7,63}$ ]] || {
  echo GOLD48_RUN_ID_HOLD >&2
  exit 42
}
case "$ROLE" in
  base|r46_v02|r54_v03a|r60_base336) ;;
  *) echo GOLD48_ROLE_HOLD >&2; exit 42 ;;
esac

export PYTHONUNBUFFERED=1
export HF_HUB_DISABLE_TELEMETRY=1
export TOKENIZERS_PARALLELISM=false

if [[ "$ACTION" == check ]]; then
  exec python "$ENTRY" check --run-id "$RUN_ID" --model-role "$ROLE"
fi

# Production mode is reached only after the Owner Mac's explicit --execute submit.
# Never allocate CUDA or load weights before the RO input preflight is accepted.
BOOTSTRAP="$(mktemp -d /tmp/storyforge-g48-bootstrap.XXXXXXXX)"
chmod 0700 "$BOOTSTRAP"
trap 'rm -rf "$BOOTSTRAP"' EXIT

if ! python "$ENTRY" check --run-id "$RUN_ID" --model-role "$ROLE" \
  > "$BOOTSTRAP/check.safe" 2> "$BOOTSTRAP/check.private"; then
  echo GOLD48_INPUT_PREFLIGHT_HOLD >&2
  exit 42
fi
if ! grep -Fq '"status": "GOLD48_FIXED_RO_STAGE_VERIFIED__NO_GPU"' \
  "$BOOTSTRAP/check.safe"; then
  echo GOLD48_INPUT_PREFLIGHT_HOLD >&2
  exit 42
fi

# Reuse the pinned, already CPU-verified --require-hashes installation.
# Do not create a new dependency resolver or silently upgrade Torch.
if ! python -m pip install --disable-pip-version-check -q --require-hashes \
  -r "$LOCK" > "$BOOTSTRAP/pip.private" 2>&1; then
  echo GOLD48_HASH_LOCK_INSTALL_HOLD >&2
  exit 42
fi
if ! python -m pip check > "$BOOTSTRAP/pip-check.private" 2>&1; then
  echo GOLD48_PIP_CHECK_HOLD >&2
  exit 42
fi

python "$ENTRY" execute --run-id "$RUN_ID" --model-role "$ROLE" \
  --explicit-owner-gpu-execution
