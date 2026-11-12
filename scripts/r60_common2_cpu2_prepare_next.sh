#!/usr/bin/env bash
# R60 Common2 CPU2: build a NEW immutable Stage from the ORIGINAL frozen input,
# sync it once, and dry-run; NEVER submits a HF Job.
set -euo pipefail
umask 077
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
command -v hf >/dev/null || { echo R60_HF_CLI_MISSING >&2; exit 42; }
[[ "$(command -v hf)" == "/opt/homebrew/bin/hf" && "$(hf --version)" == "2.4.0" ]] || {
  echo R60_HF_CLI_VERSION_HOLD >&2; exit 42;
}
PY="${R60_HF_SDK_PYTHON:-$HOME/.local/share/storyforge/venvs/hf-cli/bin/python}"
"$PY" -c "import huggingface_hub" >/dev/null 2>&1 || {
  echo R60_HF_SDK_MISSING >&2; exit 42;
}
BASE="$HOME/.local/share/storyforge/r60/hf-cpu2-stages"
OLD_KEY="r60-common2-cpu2-20261112T032815Z-71c840b37254"
mkdir -p "$BASE"
chmod 700 "$BASE"
KEY="r60-common2-cpu2-$(date -u +%Y%m%dT%H%M%SZ)-$("$PY" -c 'import secrets; print(secrets.token_hex(6))')"
STAGE="$BASE/$KEY"
# Original frozen source is bound in stage_v2.py. Never build from the
# failed 20261112T054440Z run, and never overwrite a destination.
"$PY" scripts/r60_common2_hf_cpu_stage_v2.py \
  --old-stage "$BASE/$OLD_KEY" \
  --new-stage "$STAGE" \
  --new-run-key "$KEY"
(cd "$STAGE" && shasum -a 256 -c SHA256SUMS.txt >/dev/null) || {
  echo R60_CPU2_STAGE_SHA_HOLD >&2; exit 42;
}
"$PY" scripts/r60_common2_hf_cpu_bucket_guard.py empty "$KEY" --stage "$STAGE"
export R60_HF_SDK_PYTHON="$PY"
bash scripts/r60_common2_hf_cpu_submit.sh sync-existing "$KEY" "$STAGE"
"$PY" scripts/r60_common2_hf_cpu_cli_dry_run.py \
  --run-key "$KEY" --stage "$STAGE" --dry-run
"$PY" scripts/r60_common2_hf_cpu_final_read_only.py \
  --run-key "$KEY" --stage "$STAGE"
echo "R60_COMMON2_NEXT_RUN_KEY=$KEY"
echo "R60_COMMON2_NEXT_STAGE_READY_PASS__NO_JOB"
