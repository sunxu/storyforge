#!/usr/bin/env bash
# HF Jobs entrypoint for R18; only tokenization / label diagnostics.
set -euo pipefail

STAGE="${1:-both}"
case "$STAGE" in
  token|both) ;;
  *) echo "R18_INVALID_STAGE: $STAGE" >&2; exit 2 ;;
esac

RUN_KEY="${STORYFORGE_R18_RUN_KEY:?R18 run key required}"
if [[ ! "$RUN_KEY" =~ ^r18-[[:alnum:]-]+$ ]]; then
  echo "R18_INVALID_RUN_KEY" >&2
  exit 2
fi

BASE="/workspace/preflight/v02-r18"
CODE="$BASE/code"
INPUT="$BASE/private/StoryForge_v02_R17_Runtime_And_Label_Contract_20261013.zip"
OUT="$BASE/results/$RUN_KEY"

cd "$CODE"
mkdir -p "$OUT"
printf 'R18_STAGE=%s\nR18_REPORT_DIRECTORY=%s\n' "$STAGE" "$OUT"
python --version

if [[ "$STAGE" == "both" ]]; then
  python -m pip install --disable-pip-version-check \
    "ms-swift==4.5.3" "transformers==5.16.1" \
    "huggingface_hub>=0.35,<3" "qwen-vl-utils>=0.0.14"
else
  python -m pip install --disable-pip-version-check \
    "transformers==5.16.1" "huggingface_hub>=0.35,<3"
fi

# Never invoke swift sft or any optimizer. The Python script fails closed.
python -u "$CODE/v02_r18_hf_no_train.py" \
  --r17-zip "$INPUT" \
  --output-dir "$OUT" \
  --stage "$STAGE"
