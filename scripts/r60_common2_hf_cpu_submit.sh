#!/usr/bin/env bash
# R60 Common2: Mac stdlib + HF CLI; sync NEVER starts billable compute.
set -euo pipefail
umask 077
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
MODE="${1:-}"
[[ "$MODE" == sync || "$MODE" == submit ]] || {
  echo "Usage: bash scripts/r60_common2_hf_cpu_submit.sh sync <input-dir> [output-stage-parent]" >&2
  echo "OR: STORYFORGE_ALLOW_PAID_CPU=YES STORYFORGE_R60_COMMON2_NO_TRAIN_ONLY=YES bash scripts/r60_common2_hf_cpu_submit.sh submit <RUN_KEY> <STAGE_DIR>" >&2
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
# Paid remote CPU is deliberately NOT included in the sync step.
[[ "${STORYFORGE_ALLOW_PAID_CPU:-}" == YES ]] || { echo R60_PAID_CPU_AUTHORIZATION_REQUIRED >&2; exit 3; }
[[ "${STORYFORGE_R60_COMMON2_NO_TRAIN_ONLY:-}" == YES ]] || { echo R60_NO_TRAIN_AUTHORIZATION_REQUIRED >&2; exit 3; }
RUN_KEY="${2:?run key required}"
STAGE="${3:?local immutable stage directory required}"
[[ "$STAGE" == *"/$RUN_KEY" ]] || { echo R60_RUN_STAGE_MISMATCH >&2; exit 42; }
python3 scripts/r60_common2_hf_cpu_bucket_guard.py ready "$RUN_KEY" --stage "$STAGE"
# The remote CPU worker enforces exact stage SHA256 and never calls swift sft.
echo "R60_COMMON2_CPU2_PAID_JOB_SUBMITTING=$RUN_KEY"
hf jobs run --namespace adradar --name storyforge-r60-common2-cpu2-no-train \
  --flavor cpu-upgrade --timeout 120m \
  --env "STORYFORGE_R60_COMMON2_RUN_KEY=$RUN_KEY" \
  -v "$BUCKET:/workspace:rw" \
  pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime \
  bash "/workspace/preflight/r60/common2/cpu2/runs/$RUN_KEY/code/scripts/r60_common2_hf_cpu_worker.sh"
