#!/usr/bin/env bash
# R54 V2: sync (never a Job), submit (explicit paid authorization only).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
MODE="${1:-}"
if [[ "$MODE" != sync && "$MODE" != submit ]]; then
  echo "Usage: bash scripts/v03_r54_gpu_submit.sh sync <R53_formal_release_dir> <R53_CPU40_report.json> <R53_CPU40_intake.json>" >&2
  echo "       STORYFORGE_ALLOW_PAID_GPU=YES STORYFORGE_R54_OWNER_GPU_SCOPE=R54_31_9_V2_16STEP_ONE_EPOCH bash scripts/v03_r54_gpu_submit.sh submit <R54_RUN_KEY>" >&2
  exit 2
fi
command -v python3 >/dev/null || { echo R54_NO_PYTHON3 >&2; exit 2; }
command -v hf >/dev/null || { echo R54_NO_HF_CLI >&2; exit 2; }
BUCKET="hf://buckets/adradar/storyforge-training"
PREFIX="$BUCKET/preflight/v03-r54/gpu/runs"
CONFIG="configs/v03_r54_qlora_31_9_16step_v2.yaml"
CODES=(v03_r54_gpu_runner.py v03_r54_gpu_worker.sh
       v03_r54_gpu_readiness_v2.py v03_r54_last_step_checkpoint_gate.py
       hf_label_mask_audit.py hf_smoke_guard.py hf_job_runner.py)
if [[ "$MODE" == sync ]]; then
  RELEASE="${2:-}"; CPU_REPORT="${3:-}"; CPU_INTAKE="${4:-}"
  [[ -d "$RELEASE" && -f "$CPU_REPORT" && -f "$CPU_INTAKE" ]] || {
    echo R54_LOCAL_PRIVATE_INPUTS_MISSING >&2; exit 2;
  }
  for c in "${CODES[@]}"; do
    [[ -s "scripts/$c" ]] || { echo "R54_MISSING_SOURCE=$c" >&2; exit 2; }
  done
  [[ -s "$CONFIG" ]] || { echo R54_MISSING_CONFIG >&2; exit 2; }
  # Preserve original R53-audited ms-swift label-mask implementation;
  # merely hashing arbitrary substituted code into a new stage is insufficient.
  python3 - scripts/hf_label_mask_audit.py <<'PY_AUDITOR_PIN'
import hashlib, pathlib, sys
b=pathlib.Path(sys.argv[1]).read_bytes()
blob=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\\0'+b).hexdigest()
if blob!='15296f1d8438f40d727c84913ac658cf6de01cb4':
    raise SystemExit('R54_ORIGINAL_MASK_AUDITOR_MISMATCH')
print('R54_ORIGINAL_MASK_AUDITOR_GIT_BLOB_PASS')
PY_AUDITOR_PIN
  TMP="$(mktemp -d)"
  trap 'rm -rf "$TMP"' EXIT
  # Do NOT upload anything unless the Owner-released final source and actual
  # R53 CPU40 report/intake have passed all frozen-byte checks.
  python3 scripts/v03_r54_gpu_readiness_v2.py \
    --release-dir "$RELEASE" --cpu-report "$CPU_REPORT" \
    --cpu-intake "$CPU_INTAKE" --config "$CONFIG" \
    --out "$TMP/preflight-safe.json"
  RUN_KEY="r54-v2-$(date -u +%Y%m%dT%H%M%SZ)-$(python3 -c 'import secrets; print(f"{secrets.randbelow(900000)+100000:06d}")')"
  python3 scripts/v03_r54_gpu_remote_guard.py empty "$RUN_KEY"
  mkdir -p "$TMP/code" "$TMP/config" "$TMP/private/release"
  for c in "${CODES[@]}"; do cp "scripts/$c" "$TMP/code/$c"; done
  cp "$CONFIG" "$TMP/config/r54.yaml"
  cp "$RELEASE/train.jsonl" "$RELEASE/validation.jsonl" \
     "$RELEASE/R53_RELEASE_RECEIPT.json" "$TMP/private/release/"
  cp "$CPU_REPORT" "$TMP/private/R53_HF_CPU40_AUDIT_REPORT_PRIVATE.json"
  cp "$CPU_INTAKE" "$TMP/private/R53_CPU40_OWNER_INTAKE_VERIFIED.json"
  (cd "$TMP"; sha256sum code/* config/* private/*.json private/release/* > SHA256SUMS.txt)
  for section in code config private private/release; do
    for file in "$TMP/$section/"*; do
      [[ -f "$file" ]] || continue
      hf buckets cp "$file" "$PREFIX/$RUN_KEY/$section/$(basename "$file")"
    done
  done
  # Last object commit: half-uploaded stages never pass submit readiness.
  hf buckets cp "$TMP/SHA256SUMS.txt" "$PREFIX/$RUN_KEY/SHA256SUMS.txt"
  python3 scripts/v03_r54_gpu_remote_guard.py ready "$RUN_KEY"
  echo "R54_RUN_KEY=$RUN_KEY"
  echo "R54_SYNC_READY_NO_GPU_JOB=$PREFIX/$RUN_KEY/"
  echo R54_PAID_GPU_SUBMIT_NOT_EXECUTED
  exit 0
fi

# The command below is NEVER reached by sync or verify. GPU billing approval
# is independent of the earlier Owner's private-data release authorization.
[[ "${STORYFORGE_ALLOW_PAID_GPU:-}" == YES ]] || { echo R54_PAID_GPU_NOT_AUTHORIZED >&2; exit 3; }
[[ "${STORYFORGE_R54_OWNER_GPU_SCOPE:-}" == R54_31_9_V2_16STEP_ONE_EPOCH ]] || {
  echo R54_EXPLICIT_SCOPE_NOT_AUTHORIZED >&2; exit 3;
}
RUN_KEY="${2:-}"
[[ "$RUN_KEY" =~ ^r54-v2-[0-9]{8}T[0-9]{6}Z-[0-9]{6}$ ]] || { echo R54_INVALID_SUBMIT_KEY >&2; exit 2; }
python3 scripts/v03_r54_gpu_remote_guard.py ready "$RUN_KEY"
# Conservative idempotency gate: record the attempt BEFORE invoking a billable
# API. A failed/uncertain submit is NOT silently retried with the same key.
LOCAL_LOCK="$HOME/.local/state/storyforge/r54-gpu-submit/$RUN_KEY"
mkdir -p "$(dirname "$LOCAL_LOCK")"
mkdir "$LOCAL_LOCK" || { echo R54_LOCAL_RUN_KEY_ALREADY_SUBMITTED >&2; exit 3; }
printf 'R54_SUBMIT_ATTEMPT_REGISTERED_NO_AUTORETRY %s\n' "$RUN_KEY" > "$LOCAL_LOCK/submit-attempt.txt"
# Separate remote submission marker; cross-machine check is best-effort,
# not a fully atomic distributed lock across clients.
hf buckets cp "$LOCAL_LOCK/submit-attempt.txt" \
  "$BUCKET/preflight/v03-r54/gpu/submissions/$RUN_KEY/submit-attempt.txt" || {
    echo R54_REMOTE_SUBMISSION_MARKER_FAILED__INVESTIGATE_NO_AUTORETRY >&2; exit 2;
  }
echo "R54_PAID_ONE_A100_JOB_KEY=$RUN_KEY"
echo "R54_EXPERIMENT_PREFIX=$BUCKET/experiments/v03-r54/$RUN_KEY/"
hf jobs run --namespace adradar --name storyforge-r54-v2-31-9-16step \
  --flavor a100-large --timeout 120m \
  --env "STORYFORGE_R54_RUN_KEY=$RUN_KEY" \
  --env STORYFORGE_R54_PAID_GPU_SCOPE=R54_31_9_V2_16STEP_ONE_EPOCH \
  -v "$BUCKET:/workspace:rw" \
  pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime \
  bash "/workspace/preflight/v03-r54/gpu/runs/$RUN_KEY/code/v03_r54_gpu_worker.sh"
