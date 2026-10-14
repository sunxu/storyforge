#!/usr/bin/env bash
# R48 original Gold+3 models: freeze actual scored Git CSVs before optional unblind.
# Local, CPU-only, no GPU/ZIP/LFS, and NEVER commit the private answer key.
set -euo pipefail
umask 077

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
ACTION="${1:-check}"
[[ "$ACTION" == check || "$ACTION" == unblind ]] || {
  echo 'Usage: bash scripts/v02_r48_unblind_git.sh [check|unblind]' >&2
  exit 2
}

R48="${STORYFORGE_R48_ROOT:-$HOME/.local/share/storyforge/r48/r48-20261014-gold-four-arm-20}"
REV="evaluations/v0.2/r48/reviews/round1"
MANIFEST="evaluations/v0.1/test/manifest.json"
REPORT="$R48/coordinator/R48_PRIVATE_UNBLIND_DIAGNOSTIC.json"
FREEZE="$R48/coordinator/R48_COMPLETED_REVIEWS_FREEZE.json"
KEY="$R48/coordinator/private/R48_PRIVATE_ANSWER_KEY.json"

for path in \
  "$REV/R48_Reviewer_01_completed.csv" \
  "$REV/R48_Reviewer_02_completed.csv" \
  "$REV/R48_Reviewer_03_completed.csv" \
  "$R48/reviewers/R48_Reviewer_01.csv" \
  "$R48/reviewers/R48_Reviewer_02.csv" \
  "$R48/reviewers/R48_Reviewer_03.csv"; do
  [[ -s "$path" ]] || { echo "Missing completed/original review CSV: $path" >&2; exit 2; }
done

# Committed files are locked to their exact Git blob identities; all four
# response bodies independently checked against R47+canonical Gold.
python3 scripts/v02_r48_review_freeze.py

# Score-only check never looks at mapping; compare every source field
# against the locally generated, still-blank original R48 reviewer template.
python3 scripts/v02_r48_review_aggregate.py \
  --pristine-dir "$R48/reviewers" \
  --manifest "$MANIFEST" \
  --reviews \
    "$REV/R48_Reviewer_01_completed.csv" \
    "$REV/R48_Reviewer_02_completed.csv" \
    "$REV/R48_Reviewer_03_completed.csv"

if [[ "$ACTION" == check ]]; then
  echo R48_PREUNBLIND_SOURCE_AND_RATINGS_PASS_NO_KEY_READ
  exit 0
fi

[[ "${STORYFORGE_R48_OWNER_UNBLIND:-}" == YES ]] || {
  echo R48_UNBLIND_REQUIRES_STORYFORGE_R48_OWNER_UNBLIND_YES >&2
  exit 3
}
[[ -s "$KEY" ]] || { echo "Missing coordinator-only key: $KEY" >&2; exit 2; }
[[ ! -e "$REPORT" && ! -e "$FREEZE" ]] || {
  echo R48_REFUSING_TO_OVERWRITE_PRIVATE_AUDIT >&2
  exit 2
}

# The key is passed only to the coordinator-only aggregator, after two passes.
python3 scripts/v02_r48_review_freeze.py --output "$FREEZE"
python3 scripts/v02_r48_review_aggregate.py \
  --pristine-dir "$R48/reviewers" \
  --manifest "$MANIFEST" \
  --reviews \
    "$REV/R48_Reviewer_01_completed.csv" \
    "$REV/R48_Reviewer_02_completed.csv" \
    "$REV/R48_Reviewer_03_completed.csv" \
  --key "$KEY" \
  --output "$REPORT"
echo R48_PRIVATE_UNBLIND_SUCCESS_NO_GPU
echo "R48_PRIVATE_AGGREGATE=$REPORT"
echo 'Do not commit the private answer key, local source data, or unblinding report unless intentionally approved.'
