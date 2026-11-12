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
  python3 scripts/r60_common2_hf_cpu_bucket_guard.py empty "$RUN_KEY" --stage "$STAGE"
  while IFS= read -r -d '' source; do
    rel="${source#"$STAGE/"}"
    hf buckets cp "$source" "$PREFIX/runs/$RUN_KEY/$rel"
  done < <(find "$STAGE/code" "$STAGE/private_stage" -type f -print0)
  # Upload manifest last; a partially synced run cannot be executed.
  hf buckets cp "$STAGE/SHA256SUMS.txt" "$PREFIX/runs/$RUN_KEY/SHA256SUMS.txt"
  python3 scripts/r60_common2_hf_cpu_bucket_guard.py ready "$RUN_KEY" --stage "$STAGE"
  echo "R60_COMMON2_RUN_KEY=$RUN_KEY"
  echo "R60_COMMON2_PRIVATE_STAGE_DIR=$STAGE"
  echo "R60_COMMON2_SYNC_READY__NO_JOB"
  exit 0
fi
# The explicit submit action starts the CPU job; no redundant paid-authorization flags.
# Keep sync and submit separate, with no GPU, training or automatic retry.
RUN_KEY="${2:?run key required}"
STAGE="${3:?local immutable stage directory required}"
[[ "$STAGE" == *"/$RUN_KEY" ]] || { echo R60_RUN_STAGE_MISMATCH >&2; exit 42; }
python3 scripts/r60_common2_hf_cpu_bucket_guard.py ready "$RUN_KEY" --stage "$STAGE"
(cd "$STAGE" && shasum -a 256 -c SHA256SUMS.txt >/dev/null) || {
  echo R60_LOCAL_STAGE_SHA_HOLD >&2; exit 42;
}
# An atomic persistent marker prevents accidental duplicate billing for this exact run.
# Fail closed even if HF CLI exits ambiguously after server-side job submission.
ATTEMPT="${STAGE}.cpu-submit-attempted"
if ! mkdir -m 700 "$ATTEMPT" 2>/dev/null; then
  echo R60_CPU2_DUPLICATE_SUBMIT_HOLD >&2; exit 42
fi
# The remote CPU worker enforces exact stage SHA256 and never calls swift sft.
echo "R60_COMMON2_CPU2_PAID_JOB_SUBMITTING=$RUN_KEY"
hf jobs run --namespace adradar --name storyforge-r60-common2-cpu2-no-train \
  --flavor cpu-upgrade --timeout 120m \
  --env "STORYFORGE_R60_COMMON2_RUN_KEY=$RUN_KEY" \
  -v "$BUCKET:/workspace:rw" \
  pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime \
  bash "/workspace/preflight/r60/common2/cpu2/runs/$RUN_KEY/code/scripts/r60_common2_hf_cpu_worker.sh"
