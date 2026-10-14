#!/usr/bin/env bash
# R48: add the original human Gold replies as fourth reference, CPU-only.
# Runs locally from Git and existing R47 saved inference, no HF job or ZIP.
set -euo pipefail
umask 077
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
command -v python3 >/dev/null || { echo 'python3 missing' >&2; exit 2; }
R47="$HOME/.local/share/storyforge/r47/r47-20261014T091647Z-637890/coordinator"
DEST="${STORYFORGE_R48_OUT:-$HOME/.local/share/storyforge/r48/r48-20261014-gold-four-arm-20}"
if [[ -e "$DEST" ]]; then
  echo "R48_OUT_ALREADY_EXISTS: $DEST" >&2
  exit 2
fi
if [[ ! -s data/compiled/v0.3/test.jsonl ]]; then
  echo "Canonical original Test reply source missing; don't substitute historical candidates" >&2
  exit 2
fi
if [[ ! -s "$R47/R47_PRIVATE_RUN_REPORT.json" ]]; then
  echo "Original verified R47 collected reports missing: $R47" >&2
  exit 2
fi
python3 scripts/v02_r48_four_arm_build.py \
  --compiled-test data/compiled/v0.3/test.jsonl \
  --prompts evaluations/v0.1/test/prompts.jsonl \
  --manifest evaluations/v0.1/test/manifest.json \
  --r47-coordinator "$R47" \
  --out-dir "$DEST"
echo R48_FOUR_ARM_REVIEW_PREPARED_NO_GPU
echo "R48_OUT=$DEST"
echo 'Send ONLY R48_Reviewer_01/02/03.csv individually to independent blind reviewers.'
echo 'Do not provide coordinator/private/R48_PRIVATE_ANSWER_KEY.json or R47 graded results.'
