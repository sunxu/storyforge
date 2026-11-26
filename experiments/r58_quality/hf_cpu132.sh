#!/usr/bin/env bash
# R58 HF CPU132: explicit sync / paid submit / verify. Never automatically submit.
set -euo pipefail
umask 077
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
ACTION="${1:-}"
[[ "$ACTION" == sync || "$ACTION" == submit || "$ACTION" == verify ]] || {
 echo 'Usage: bash experiments/r58_quality/hf_cpu132.sh sync|submit RUN_KEY|verify RUN_KEY' >&2
 exit 2
}
command -v hf >/dev/null || { echo HF_CLI_MISSING >&2; exit 2; }
BUCKET='adradar/storyforge-training'
BASE="hf://buckets/$BUCKET"
PREFIX="$BASE/preflight/r58/hf-cpu132"
LOCAL="$HOME/.local/share/storyforge/r58/hf-cpu132-runs"
SOURCE="$HOME/.local/share/storyforge/r58/hf-semantic-review132-v1/input132.private.jsonl"
hf auth whoami >/dev/null
INFO="$(hf buckets info "$BUCKET")"
python3 - "$INFO" "$BUCKET" <<'PY_CHECK'
import json,sys
x=json.loads(sys.argv[1])
if x.get("private") is not True or x.get("id") != sys.argv[2]:
 raise SystemExit("R58_BUCKET_PRIVACY_NOT_VERIFIED__HOLD")
PY_CHECK

if [[ "$ACTION" == sync ]]; then
 [[ -f "$SOURCE" ]] || { echo R58_PRIVATE_INPUT_MISSING >&2; exit 2; }
 RUN_KEY="r58-hfcpu132-$(date -u +%Y%m%dT%H%M%SZ)-$(python3 -c 'import secrets;print(secrets.randbelow(900000)+100000)')"
 mkdir -p "$LOCAL"
 chmod 700 "$LOCAL"
 STAGE="$LOCAL/$RUN_KEY/stage"
 mkdir -m 700 "$LOCAL/$RUN_KEY"
 python3 experiments/r58_quality/gold195_hf_review_cpu_stage.py \
   --repo-root "$ROOT" --private-input "$SOURCE" --stage-dir "$STAGE"
 # Fail closed on existing object prefix: inspect tree, not CLI zero exit status.
 python3 - "$BUCKET" "$RUN_KEY" <<'PY_EMPTY'
from huggingface_hub import HfApi
import sys
bucket,key=sys.argv[1:]
prefix=f"preflight/r58/hf-cpu132/runs/{key}/"
objects=list(HfApi().list_bucket_tree(bucket,prefix=prefix,recursive=True))
if objects:
 raise SystemExit("R58_REMOTE_RUN_PREFIX_EXISTS__HOLD")
PY_EMPTY
 for NAME in code/gold195_hf_review_cpu_worker.py \
             code/gold195_hf_review_gpu_runner.py \
             code/gold195_hf_review_cpu_bootstrap.py \
             private/input132.private.jsonl; do
   hf buckets cp "$STAGE/$NAME" "$PREFIX/runs/$RUN_KEY/$NAME" >/dev/null
 done
 # Upload checksum manifest LAST.
 hf buckets cp "$STAGE/SHA256SUMS.txt" "$PREFIX/runs/$RUN_KEY/SHA256SUMS.txt" >/dev/null
 TMP="$(mktemp -d)"
 trap 'rm -rf "$TMP"' EXIT
 for NAME in code/gold195_hf_review_cpu_worker.py \
             code/gold195_hf_review_gpu_runner.py \
             code/gold195_hf_review_cpu_bootstrap.py \
             private/input132.private.jsonl SHA256SUMS.txt; do
   mkdir -p "$TMP/$(dirname "$NAME")"
   hf buckets cp "$PREFIX/runs/$RUN_KEY/$NAME" "$TMP/$NAME" >/dev/null
   cmp -s "$TMP/$NAME" "$STAGE/$NAME" || { echo R58_REMOTE_BYTES_MISMATCH__HOLD >&2; exit 2; }
 done
 echo "R58_CPU132_RUN_KEY=$RUN_KEY"
 echo R58_HF_CPU132_REMOTE_STAGE_BYTES_PASS__NO_JOB
 exit 0
fi

RUN_KEY="${2:-}"
[[ "$RUN_KEY" =~ ^r58-hfcpu132-[0-9]{8}T[0-9]{6}Z-[0-9]{6}$ ]] || {
 echo R58_RUN_KEY_INVALID >&2; exit 2;
}
STAGE="$LOCAL/$RUN_KEY/stage"
[[ -d "$STAGE" ]] || { echo R58_LOCAL_STAGE_MISSING >&2; exit 2; }
python3 "$STAGE/code/gold195_hf_review_cpu_worker.py" \
  --stage "$STAGE" --result-dir "$LOCAL/nonexistent" --run-key "$RUN_KEY" >/dev/null

if [[ "$ACTION" == submit ]]; then
 [[ "${STORYFORGE_ALLOW_PAID_CPU:-}" == YES && "${STORYFORGE_R58_CPU132_NO_GPU:-}" == YES ]] || {
  echo R58_PAID_CPU_NOT_AUTHORIZED__HOLD >&2; exit 3;
 }
 # Re-download all four objects before considering a paid submission.
 TMP="$(mktemp -d)"
 trap 'rm -rf "$TMP"' EXIT
 for NAME in code/gold195_hf_review_cpu_worker.py \
             code/gold195_hf_review_gpu_runner.py \
             code/gold195_hf_review_cpu_bootstrap.py \
             private/input132.private.jsonl SHA256SUMS.txt; do
   mkdir -p "$TMP/$(dirname "$NAME")"
   hf buckets cp "$PREFIX/runs/$RUN_KEY/$NAME" "$TMP/$NAME" >/dev/null
   cmp -s "$TMP/$NAME" "$STAGE/$NAME" || { echo R58_REMOTE_BYTES_MISMATCH__HOLD >&2; exit 2; }
 done
 mkdir -m 700 "$LOCAL/$RUN_KEY/submit-attempted" || {
   echo R58_SUBMIT_ALREADY_ATTEMPTED__HOLD >&2; exit 3;
 }
 hf jobs run --namespace adradar --name storyforge-r58-cpu132-token-only \
   --flavor cpu-upgrade --timeout 90m -v "$BASE:/workspace:rw" \
   python:3.12-slim python \
   "/workspace/preflight/r58/hf-cpu132/runs/$RUN_KEY/code/gold195_hf_review_cpu_bootstrap.py" \
   "$RUN_KEY"
 exit 0
fi

DIR="$LOCAL/$RUN_KEY/results"
[[ ! -e "$DIR" ]] || { echo R58_RESULTS_ALREADY_EXIST__HOLD >&2; exit 2; }
mkdir -m 700 "$DIR"
hf buckets cp "$PREFIX/results/$RUN_KEY/R58_HF_CPU132_SAFE.json" "$DIR/R58_HF_CPU132_SAFE.json" >/dev/null
chmod 600 "$DIR/R58_HF_CPU132_SAFE.json"
python3 - "$DIR/R58_HF_CPU132_SAFE.json" <<'PY_VERIFY'
import json,sys
obj=json.load(open(sys.argv[1]))
c=obj.get("counts",{})
assert obj.get("schema")=="r58_hf_cpu132_tokenizer_safe_v2"
assert obj.get("status")=="R58_HF_CPU132_REAL_TOKEN_IDS_VERIFIED__NO_INFERENCE"
assert obj.get("source_rows_verified")==132
assert obj.get("token_length_source")=="input_ids"
assert obj.get("model_revision")=="9216db5781bf21249d130ec9da846c4624c16137"
assert obj.get("quality_v1_admitted")==0
assert obj.get("gpu_used") is False and obj.get("training_performed") is False
assert c.get("cases_total")==132 and c.get("fits_context",0)+c.get("token_hold",0)==132
assert type(c.get("prompt_tokens_min")) is int and c["prompt_tokens_min"]>=32
assert c["prompt_tokens_min"]<=c["prompt_tokens_median"]<=c["prompt_tokens_p95"]<=c["prompt_tokens_max"]
print(json.dumps({"status":"R58_HF_CPU132_SAFE_REPORT_VALIDATED__NOT_ADMITTED",
                  "counts":c,"quality_v1_admitted":0,"gpu_used":False,
                  "private_text_emitted":False},sort_keys=True))
PY_VERIFY
