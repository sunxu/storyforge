#!/usr/bin/env bash
# HF Bucket sync by default; explicitly gated PAID cpu-upgrade submit only.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
ACTION="${1:-}"
if [[ "$ACTION" != sync && "$ACTION" != submit ]]; then
  echo "Usage: bash scripts/v03_r53_hf_cpu40_submit.sh sync /private_stage_dir" >&2
  echo "   OR: STORYFORGE_ALLOW_PAID_CPU=YES STORYFORGE_R53_CPU40_NO_TRAIN_ONLY=YES bash scripts/v03_r53_hf_cpu40_submit.sh submit <R53_RUN_KEY>" >&2
  exit 2
fi
command -v hf >/dev/null || { echo R53_HF_CLI_MISSING >&2; exit 2; }
command -v python3 >/dev/null || { echo R53_PYTHON3_MISSING >&2; exit 2; }
BASE="hf://buckets/adradar/storyforge-training"
PREFIX="$BASE/preflight/v03-r53/cpu40"
if [[ "$ACTION" == sync ]]; then
  STAGE="${2:-}"
  [[ -d "$STAGE" ]] || { echo R53_PRIVATE_STAGE_MISSING >&2; exit 2; }
  for f in v03_r53_hf_cpu40_audit.py v03_r53_hf_cpu40_worker.sh v03_r53_hf_bucket_prefix_guard.py hf_label_mask_audit.py; do
    [[ -s "scripts/$f" ]] || { echo "R53_MISSING_CODE: $f" >&2; exit 2; }
  done
  python3 scripts/v03_r53_hf_cpu40_audit.py preflight --stage "$STAGE"
  # Upstream mask implementation must be the audited original Git file.
  python3 - scripts/hf_label_mask_audit.py <<'PY'
import hashlib, pathlib, sys
p=pathlib.Path(sys.argv[1]); b=p.read_bytes()
digest=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
if digest!='15296f1d8438f40d727c84913ac658cf6de01cb4':
    raise SystemExit('R53_OFFICIAL_MASK_AUDITOR_CODE_MISMATCH')
print('R53_PINNED_AUDITOR_SOURCE_PASS')
PY
  RUN_KEY="r53-cpu40-$(date -u +%Y%m%dT%H%M%SZ)-$(python3 -c 'import secrets; print(f"{secrets.randbelow(900000)+100000:06d}")')"
  TMP="$(mktemp -d)"
  trap 'rm -rf "$TMP"' EXIT
  mkdir -p "$TMP/code" "$TMP/private_stage"
  for f in v03_r53_hf_cpu40_audit.py v03_r53_hf_cpu40_worker.sh hf_label_mask_audit.py; do
    cp "scripts/$f" "$TMP/code/$f"
  done
  for f in STAGED_31_9_SOURCE_HASH_MANIFEST_PRIVATE.json STAGED_TRAIN_NOT_ADMITTED.jsonl STAGED_VALIDATION_NOT_ADMITTED.jsonl; do
    cp "$STAGE/$f" "$TMP/private_stage/$f"
  done
  (cd "$TMP"; sha256sum code/* private_stage/* > SHA256SUMS.txt)
  # hf buckets ls may return exit 0 for an EMPTY prefix; success != existence.
  # The SDK must confirm there are ZERO objects; auth/network errors block sync.
  python3 scripts/v03_r53_hf_bucket_prefix_guard.py empty "$RUN_KEY"
  for f in "$TMP/code/"*; do hf buckets cp "$f" "$PREFIX/runs/$RUN_KEY/code/$(basename "$f")"; done
  for f in "$TMP/private_stage/"*; do hf buckets cp "$f" "$PREFIX/runs/$RUN_KEY/private_stage/$(basename "$f")"; done
  # Upload manifest last: the worker never accepts a partially synced run.
  hf buckets cp "$TMP/SHA256SUMS.txt" "$PREFIX/runs/$RUN_KEY/SHA256SUMS.txt"
  echo "R53_RUN_KEY=$RUN_KEY"
  echo "R53_SYNC_READY_NO_JOB=$PREFIX/runs/$RUN_KEY/"
  echo "R53_SUBMIT_NOT_EXECUTED__NO_CPU_CHARGE"
  exit 0
fi
# Explicitly separate paid CPU authorization from sync.
[[ "${STORYFORGE_ALLOW_PAID_CPU:-}" == YES ]] || { echo R53_PAID_CPU_NOT_AUTHORIZED >&2; exit 3; }
[[ "${STORYFORGE_R53_CPU40_NO_TRAIN_ONLY:-}" == YES ]] || { echo R53_CPU40_SCOPE_NOT_AUTHORIZED >&2; exit 3; }
RUN_KEY="${2:-}"
[[ "$RUN_KEY" =~ ^r53-cpu40-[0-9]{8}T[0-9]{6}Z-[0-9]{6}$ ]] || { echo R53_INVALID_SUBMIT_RUN_KEY >&2; exit 2; }
# Reject a missing/partial run before starting any billable CPU Job.
python3 scripts/v03_r53_hf_bucket_prefix_guard.py ready "$RUN_KEY"
echo "R53_PAID_CPU_JOB_SUBMISSION_KEY=$RUN_KEY"
echo "R53_RESULT_PREFIX=$PREFIX/results/$RUN_KEY/"
hf jobs run --namespace adradar --name storyforge-r53-cpu40-labelmask-no-train \
  --flavor cpu-upgrade --timeout 120m \
  --env "STORYFORGE_R53_RUN_KEY=$RUN_KEY" \
  -v "$BASE:/workspace:rw" \
  pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime \
  bash "/workspace/preflight/v03-r53/cpu40/runs/$RUN_KEY/code/v03_r53_hf_cpu40_worker.sh"
