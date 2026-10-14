#!/usr/bin/env bash
# Read-only R47 finished-job collection from the existing private HF Bucket.
# No GPU, training, ZIP, LFS or Git commit of story text.
set -euo pipefail
umask 077
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
command -v hf >/dev/null || { echo 'Hugging Face CLI missing' >&2; exit 2; }
command -v python3 >/dev/null || { echo 'python3 missing' >&2; exit 2; }
RUN_KEY='r47-20261014T091647Z-637890'
PREFIX="hf://buckets/adradar/storyforge-training/evaluation-runs/v02-r47/$RUN_KEY"
DEST="${STORYFORGE_R47_LOCAL_OUT:-$HOME/.local/share/storyforge/r47/$RUN_KEY}"
if [[ -e "$DEST" ]]; then
  echo "Refusing to overwrite an existing collection: $DEST" >&2
  exit 2
fi
mkdir -p "$DEST/coordinator/private" "$DEST/reviewers"
hf buckets cp "$PREFIX/R47_PRIVATE_RUN_REPORT.json" \
  "$DEST/coordinator/R47_PRIVATE_RUN_REPORT.json"
for arm in base v01 v02; do
  hf buckets cp "$PREFIX/$arm-results.jsonl" "$DEST/coordinator/$arm-results.jsonl"
done
hf buckets cp "$PREFIX/review-package/blind-review/R47_BLIND_THREE_WAY_20.jsonl" \
  "$DEST/reviewers/R47_BLIND_THREE_WAY_20.jsonl"
for number in 01 02 03; do
  hf buckets cp "$PREFIX/review-package/blind-review/R47_Reviewer_$number.csv" \
    "$DEST/reviewers/R47_Reviewer_$number.csv"
done
hf buckets cp "$PREFIX/review-package/private/R47_PRIVATE_ANSWER_KEY.json" \
  "$DEST/coordinator/private/R47_PRIVATE_ANSWER_KEY.json"
hf buckets cp "$PREFIX/review-package/private/R47_AUDIT_SUMMARY.json" \
  "$DEST/coordinator/private/R47_AUDIT_SUMMARY.json"
python3 "$ROOT/scripts/v02_r47_collect_validate.py" \
  --directory "$DEST" \
  --prompts "$ROOT/evaluations/v0.1/test/prompts.jsonl" \
  --manifest "$ROOT/evaluations/v0.1/test/manifest.json"
echo R47_COLLECTION_COMPLETE_NO_GPU
echo 'Share only the assigned reviewer CSV with each reviewer.'
