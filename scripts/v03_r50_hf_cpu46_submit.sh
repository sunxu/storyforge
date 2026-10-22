#!/usr/bin/env bash
# StoryForge R50: SYNC != SUBMIT != VERIFY. Mac needs hf CLI + Python stdlib only.
set -euo pipefail
umask 077
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
ACTION="${1:-}"
[[ "$ACTION" == sync || "$ACTION" == submit || "$ACTION" == verify ]] || {
  echo 'Usage: bash scripts/v03_r50_hf_cpu46_submit.sh sync | submit RUN_KEY | verify RUN_KEY' >&2; exit 2;
}
BUCKET_ID="${STORYFORGE_R50_HF_BUCKET_ID:-adradar/storyforge-r50-audit}"
JOB_NAMESPACE="${STORYFORGE_R50_HF_NAMESPACE:-adradar}"
[[ "$BUCKET_ID" =~ ^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$ ]] || { echo R50_HF_BUCKET_ID_INVALID >&2; exit 2; }
[[ "$JOB_NAMESPACE" =~ ^[A-Za-z0-9._-]+$ ]] || { echo R50_HF_NAMESPACE_INVALID >&2; exit 2; }
# R50 audit Jobs and their Bucket MUST remain under the existing adradar organization.
[[ "$JOB_NAMESPACE" == adradar && "$BUCKET_ID" == adradar/* ]] || {
  echo R50_ORG_NAMESPACE_MISMATCH__REQUIRE_ADRADAR >&2; exit 2;
}
# Strictly forbid sharing R50 with historical training storage and the auto jobs-artifacts bucket.
[[ "$BUCKET_ID" != adradar/storyforge-training && "$BUCKET_ID" != */jobs-artifacts ]] || {
  echo R50_PROTECTED_BUCKET_MUST_BE_SEPARATE >&2; exit 2;
}
BUCKET="hf://buckets/$BUCKET_ID"
PREFIX="$BUCKET/preflight/r50/cpu46"
LOCAL="${STORYFORGE_R50_HF_LOCAL_ROOT:-$HOME/.local/share/storyforge/r50/hf-cpu46}"
# Reject private output/staging nested under any Git checkout, including the StoryForge source tree.
python3 - "$ROOT" "$LOCAL" <<'PY_SCOPE'
from pathlib import Path
import sys
repo=Path(sys.argv[1]).resolve()
root=Path(sys.argv[2]).expanduser().resolve()
if root == repo or repo in root.parents:
    raise SystemExit('R50_PRIVATE_STAGING_MUST_STAY_OUTSIDE_CODE_TREE')
PY_SCOPE
command -v hf >/dev/null || { echo R50_HF_CLI_MISSING >&2; exit 2; }
command -v python3 >/dev/null || { echo R50_PYTHON3_MISSING >&2; exit 2; }
command -v git >/dev/null || { echo R50_GIT_MISSING >&2; exit 2; }
[[ -f scripts/v03_r50_hf_cpu46_audit.py && -f scripts/v03_r50_hf_cpu46_worker.sh ]] || {
  echo R50_EXPECTED_CODE_MISSING >&2; exit 2;
}
# Validate bucket as PRIVATE before any upload / job / retrieval. HF CLI JSON docs.
hf auth whoami >/dev/null
bucket_info="$(hf buckets info "$BUCKET_ID")" || { echo R50_PRIVATE_BUCKET_UNAVAILABLE >&2; exit 2; }
python3 - "$BUCKET_ID" "$bucket_info" <<'PY'
import json,sys
try:
    info=json.loads(sys.argv[2]); ok=info.get('id')==sys.argv[1] and info.get('private') is True
except Exception:
    ok=False
if not ok:
    raise SystemExit('R50_BUCKET_NOT_CONFIRMED_PRIVATE__HOLD')
print('R50_BUCKET_PRIVATE_VERIFIED')
PY

sha_file() { shasum -a 256 "$1" | awk '{print $1}'; }
# Any failure to list remote objects is a hard failure; no assumptions from empty prefix return codes.
remote_list() { hf buckets ls "$BUCKET_ID" -R; }
remote_validate_exact() {
  local key="$1" stage="$2" temp list_expected item name
  [[ "$key" =~ ^r50-cpu46-[0-9]{8}T[0-9]{6}Z-[0-9]{6}$ ]] || { echo R50_INVALID_RUN_KEY >&2; return 2; }
  python3 scripts/v03_r50_hf_cpu46_audit.py check-stage --stage "$stage" >/dev/null
  temp="$(mktemp -d)"
  # Download only the six known objects; we do not claim to verify an object without remote bytes.
  for name in code/v03_r50_hf_cpu46_audit.py code/v03_r50_hf_cpu46_worker.sh \
    private/R50_CANDIDATE_46_PRESEAL_PRIVATE.jsonl \
    private/R45_SYSTEM_CANDIDATE_64_OF_64_NOT_APPROVED_PRIVATE.txt \
    private/R50_CPU_TOKENIZER_PREFLIGHT_46.py SHA256SUMS.txt; do
    mkdir -p "$temp/$(dirname "$name")"
    if ! hf buckets cp "$PREFIX/runs/$key/$name" "$temp/$name" >/dev/null; then
      echo R50_REMOTE_OBJECT_DOWNLOAD_FAILED >&2; rm -rf "$temp"; return 2
    fi
    if [[ "$(sha_file "$stage/$name")" != "$(sha_file "$temp/$name")" ]]; then
      echo R50_REMOTE_BYTE_PIN_MISMATCH >&2; rm -rf "$temp"; return 2
    fi
  done
  python3 scripts/v03_r50_hf_cpu46_audit.py check-stage --stage "$temp" >/dev/null || {
    echo R50_REMOTE_PACKAGE_INTEGRITY_HOLD >&2; rm -rf "$temp"; return 2;
  }
  rm -rf "$temp"
  echo R50_REMOTE_STAGE_6_OF_6_BYTES_MATCH__NO_JOB
}

if [[ "$ACTION" == sync ]]; then
  # Explicit environment inputs win. Otherwise find under approved private directories only.
  lookup() {
    local given="$1" filename="$2" result
    if [[ -n "$given" ]]; then
      [[ -f "$given" && ! -L "$given" ]] || { echo R50_REQUIRED_PRIVATE_INPUT_MISSING >&2; return 2; }
      printf '%s\n' "$given"; return
    fi
    result="$(find "$HOME/.local/share/storyforge/r50" "$HOME/Downloads" \
      -type f -name "$filename" -print -quit 2>/dev/null || true)"
    [[ -f "$result" && ! -L "$result" ]] || { echo R50_REQUIRED_PRIVATE_INPUT_MISSING >&2; return 2; }
    printf '%s\n' "$result"
  }
  CASES="$(lookup "${R50_CASES:-}" R50_CANDIDATE_46_PRESEAL_PRIVATE.jsonl)"
  SYSTEM="$(lookup "${R50_SYSTEM:-}" R45_SYSTEM_CANDIDATE_64_OF_64_NOT_APPROVED_PRIVATE.txt)"
  PREFLIGHT="$(lookup "${R50_PREFLIGHT:-}" R50_CPU_TOKENIZER_PREFLIGHT_46.py)"
  mkdir -p "$LOCAL"
  chmod 700 "$LOCAL"
  RUN_KEY="r50-cpu46-$(date -u +%Y%m%dT%H%M%SZ)-$(python3 -c 'import secrets;print(f"{secrets.randbelow(900000)+100000:06d}")')"
  STAGE="$LOCAL/$RUN_KEY/stage"
  mkdir -m 700 "$LOCAL/$RUN_KEY"
  python3 scripts/v03_r50_hf_cpu46_audit.py stage \
    --candidates "$CASES" --system-file "$SYSTEM" --preflight "$PREFLIGHT" \
    --audit-source scripts/v03_r50_hf_cpu46_audit.py \
    --worker-source scripts/v03_r50_hf_cpu46_worker.sh \
    --stage "$STAGE"
  # Get all existing paths BEFORE write; do not trust a blank successful prefix listing.
  remote_all="$(remote_list)" || { echo R50_REMOTE_BUCKET_LIST_FAILED >&2; exit 2; }
  if [[ "$remote_all" == *"$RUN_KEY"* ]]; then
    echo R50_REMOTE_RUN_KEY_ALREADY_USED__NO_UPLOAD >&2; exit 2
  fi
  for name in code/v03_r50_hf_cpu46_audit.py code/v03_r50_hf_cpu46_worker.sh \
    private/R50_CANDIDATE_46_PRESEAL_PRIVATE.jsonl \
    private/R45_SYSTEM_CANDIDATE_64_OF_64_NOT_APPROVED_PRIVATE.txt \
    private/R50_CPU_TOKENIZER_PREFLIGHT_46.py; do
    hf buckets cp "$STAGE/$name" "$PREFIX/runs/$RUN_KEY/$name"
  done
  # Commit marker LAST; cannot treat partial upload as READY.
  hf buckets cp "$STAGE/SHA256SUMS.txt" "$PREFIX/runs/$RUN_KEY/SHA256SUMS.txt"
  remote_validate_exact "$RUN_KEY" "$STAGE"
  printf '%s\n' "$RUN_KEY" > "$LOCAL/$RUN_KEY/RUN_KEY.txt"
  echo "R50_RUN_KEY=$RUN_KEY"
  echo "R50_SYNC_READY__NO_HF_JOB=$PREFIX/runs/$RUN_KEY/"
  echo R50_NO_PAID_CPU_JOB_EXECUTED
  exit 0
fi

RUN_KEY="${2:-}"
[[ "$RUN_KEY" =~ ^r50-cpu46-[0-9]{8}T[0-9]{6}Z-[0-9]{6}$ ]] || { echo R50_INVALID_RUN_KEY >&2; exit 2; }
# Enforce explicit authorization BEFORE any expensive remote reads or paid API call.
if [[ "$ACTION" == submit ]]; then
  [[ "${STORYFORGE_ALLOW_PAID_CPU:-}" == YES && "${STORYFORGE_R50_CPU46_DRAFT_ONLY:-}" == YES ]] || {
    echo R50_PAID_CPU_SCOPE_NOT_AUTHORIZED >&2; exit 3
  }
fi
STAGE="$LOCAL/$RUN_KEY/stage"
[[ -d "$STAGE" ]] || { echo R50_PRIVATE_LOCAL_STAGE_MISSING >&2; exit 2; }
if [[ "$ACTION" == submit ]]; then
  remote_validate_exact "$RUN_KEY" "$STAGE"
  # Single shot. Missing output does not mean no Job was created: never auto resubmit.
  mkdir -p "$LOCAL/$RUN_KEY/state"
  mkdir "$LOCAL/$RUN_KEY/state/submit-attempted" || {
    echo R50_SUBMIT_ALREADY_ATTEMPTED__INVESTIGATE_JOB_LIST >&2; exit 3;
  }
  printf '%s\n' "R50_CPU46_SUBMIT_ATTEMPTED__DO_NOT_AUTO_RETRY" > "$LOCAL/$RUN_KEY/state/submit-attempted/status.txt"
  echo "R50_BILLABLE_CPU_SUBMIT_ATTEMPT_KEY=$RUN_KEY"
  echo "R50_RESULTS_PREFIX=$PREFIX/results/$RUN_KEY/"
  hf jobs run --namespace "$JOB_NAMESPACE" --name storyforge-r50-cpu46-draft \
    --flavor cpu-upgrade --timeout 90m \
    --env "STORYFORGE_R50_RUN_KEY=$RUN_KEY" \
    --env STORYFORGE_R50_CPU46_DRAFT_ONLY=YES \
    -v "$BUCKET:/workspace:rw" \
    python:3.12-slim \
    bash "/workspace/preflight/r50/cpu46/runs/$RUN_KEY/code/v03_r50_hf_cpu46_worker.sh"
  exit 0
fi

# verify: fetch actual report+hashes first; independent standard-library verifier; never print private report.
DIR="$LOCAL/$RUN_KEY/results"
[[ ! -e "$DIR" ]] || { echo R50_RESULTS_DIR_ALREADY_EXISTS__NO_OVERWRITE >&2; exit 2; }
mkdir -m 700 "$DIR"
for name in R50_CPU46_COUNT_ONLY_RECEIPT.json \
  R50_46_CPU_TOKENIZER_DRAFT_PRIVATE.json R50_CPU46_PREFLIGHT_OUTPUT_PRIVATE.txt; do
  hf buckets cp "$PREFIX/results/$RUN_KEY/$name" "$DIR/$name" >/dev/null || {
    echo R50_REMOTE_RESULT_DOWNLOAD_FAILED >&2; exit 2;
  }
done
python3 scripts/v03_r50_hf_cpu46_audit.py verify \
  --stage "$STAGE" --receipt "$DIR/R50_CPU46_COUNT_ONLY_RECEIPT.json" \
  --report "$DIR/R50_46_CPU_TOKENIZER_DRAFT_PRIVATE.json" \
  --private-log "$DIR/R50_CPU46_PREFLIGHT_OUTPUT_PRIVATE.txt" \
  --run-key "$RUN_KEY" --output "$DIR/R50_CPU46_OWNER_INTAKE_COUNT_ONLY.json"
echo "R50_SAFE_RESULT=$DIR/R50_CPU46_OWNER_INTAKE_COUNT_ONLY.json"
echo 'R50_PRIVATE_TOKEN_REPORT_STAYS_ON_OWNER_MAC_AND_PROTECTED_BUCKET'
