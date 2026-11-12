#!/usr/bin/env bash
# R60 Common2: Mac stdlib + HF CLI; sync NEVER starts billable compute.
set -euo pipefail
umask 077
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
MODE="${1:-}"
[[ "$MODE" == sync || "$MODE" == sync-existing || "$MODE" == submit ]] || {
  echo "Usage: bash scripts/r60_common2_hf_cpu_submit.sh sync <input-dir> [output-stage-parent]" >&2
  echo "OR: bash scripts/r60_common2_hf_cpu_submit.sh sync-existing <RUN_KEY> <STAGE_DIR>" >&2
  echo "OR: bash scripts/r60_common2_hf_cpu_submit.sh submit <RUN_KEY> <STAGE_DIR>" >&2
  exit 2
}
command -v hf >/dev/null || { echo R60_HF_CLI_MISSING >&2; exit 42; }
command -v python3 >/dev/null || { echo R60_PYTHON_MISSING >&2; exit 42; }
# Homebrew HF CLI and HF SDK Python may live in different environments.
HF_SDK_PYTHON="${R60_HF_SDK_PYTHON:-python3}"
"$HF_SDK_PYTHON" -c "import huggingface_hub" >/dev/null 2>&1 || {
  echo R60_HF_SDK_MISSING >&2; exit 42;
}
BUCKET="hf://buckets/adradar/storyforge-training"
PREFIX="$BUCKET/preflight/r60/common2/cpu2"
if [[ "$MODE" == sync ]]; then
  INPUT="${2:?Owner private input directory required}"
  STAGE_PARENT="${3:-$HOME/.local/share/storyforge/r60/hf-cpu2-stages}"
  mkdir -p "$STAGE_PARENT"
  chmod 700 "$STAGE_PARENT"
  RUN_KEY="r60-common2-cpu2-$(date -u +%Y%m%dT%H%M%SZ)-$(python3 -c 'import secrets; print(secrets.token_hex(6))')"
  STAGE="$STAGE_PARENT/$RUN_KEY"
  python3 scripts/r60_common2_hf_cpu_stage.py \
    --input-dir "$INPUT" --output-dir "$STAGE" --run-key "$RUN_KEY"
fi
if [[ "$MODE" == sync-existing ]]; then
  RUN_KEY="${2:?Existing run key required}"
  STAGE="${3:?Existing stage dir required}"
  [[ "$STAGE" == *"/$RUN_KEY" && -f "$STAGE/SHA256SUMS.txt" ]] || {
    echo R60_EXISTING_STAGE_MISMATCH >&2; exit 42;
  }
fi
if [[ "$MODE" == sync || "$MODE" == sync-existing ]]; then
  (cd "$STAGE" && shasum -a 256 -c SHA256SUMS.txt >/dev/null) || {
    echo R60_LOCAL_STAGE_SHA_HOLD >&2; exit 42;
  }
  "$HF_SDK_PYTHON" scripts/r60_common2_hf_cpu_bucket_guard.py empty "$RUN_KEY" --stage "$STAGE"
  while IFS= read -r -d '' source; do
    rel="${source#"$STAGE/"}"
    hf buckets cp "$source" "$PREFIX/runs/$RUN_KEY/$rel"
  done < <(find "$STAGE/code" "$STAGE/private_stage" -type f -print0)
  # Upload manifest last; a partially synced run cannot be executed.
  hf buckets cp "$STAGE/SHA256SUMS.txt" "$PREFIX/runs/$RUN_KEY/SHA256SUMS.txt"
  "$HF_SDK_PYTHON" scripts/r60_common2_hf_cpu_bucket_guard.py ready "$RUN_KEY" --stage "$STAGE"
  echo "R60_COMMON2_RUN_KEY=$RUN_KEY"
  echo "R60_COMMON2_PRIVATE_STAGE_DIR=$STAGE"
  echo "R60_COMMON2_SYNC_READY__NO_JOB"
  exit 0
fi
# Legacy submit is disabled: the old hf CLI parsed --name as a Docker image
# and mounted the entire private bucket RW, contrary to AGENTS.md section 2.3.
# Preserve sync/sync-existing modes; never create a new submit marker here.
echo R60_COMMON2_LEGACY_CLI_SUBMIT_DISABLED_MOUNT_POLICY_HOLD >&2
exit 42
