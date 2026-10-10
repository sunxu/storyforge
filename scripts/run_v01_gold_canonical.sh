#!/usr/bin/env bash
# Verify canonical v0.1 Gold and export reviewer-only comparisons (CPU only).
set -euo pipefail
umask 077

if [[ "$#" -ne 3 ]]; then
  echo "Usage: bash scripts/run_v01_gold_canonical.sh <organizer-candidate.zip> <canonical-test.jsonl> <new-output-dir>" >&2
  exit 2
fi

CANDIDATE_ZIP="$1"
CANONICAL_TEST="$2"
OUT="$3"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [[ ! -f "$CANDIDATE_ZIP" ]]; then
  echo "Missing organizer-only candidate ZIP: $CANDIDATE_ZIP" >&2
  exit 2
fi
if [[ ! -f "$CANONICAL_TEST" ]]; then
  echo "Missing canonical compiled v0.3 Test: $CANONICAL_TEST" >&2
  exit 2
fi
if [[ -e "$OUT" ]]; then
  echo "Refusing to overwrite existing output directory: $OUT" >&2
  exit 2
fi
for command in python3 unzip zip; do
  if ! command -v "$command" >/dev/null 2>&1; then
    echo "Missing required local command: $command" >&2
    exit 2
  fi
done

mkdir -p "$OUT"
# Extract only the expected file, avoiding untrusted archive paths.
unzip -p "$CANDIDATE_ZIP" TRIPLETS_INTERNAL_UNBLINDED.json > \
  "$OUT/TRIPLETS_INTERNAL_UNBLINDED.json"
if [[ ! -s "$OUT/TRIPLETS_INTERNAL_UNBLINDED.json" ]]; then
  echo "Candidate ZIP did not provide nonempty TRIPLETS_INTERNAL_UNBLINDED.json" >&2
  exit 2
fi

cd "$ROOT"
python3 scripts/audit_gold_reference.py \
  --compiled-test "$CANONICAL_TEST" \
  --prompts evaluations/v0.1/test/prompts.jsonl \
  --manifest evaluations/v0.1/test/manifest.json \
  --candidate "$OUT/TRIPLETS_INTERNAL_UNBLINDED.json" \
  --output "$OUT/canonical-gold-audit.json"

# These steps execute ONLY after CANONICAL_GOLD_MATCH_PASS (audit exit code 0).
python3 scripts/prepare_gold_comparisons.py \
  --compiled-test "$CANONICAL_TEST" \
  --prompts evaluations/v0.1/test/prompts.jsonl \
  --manifest evaluations/v0.1/test/manifest.json \
  --blind-pairs evaluations/v0.1/test/blind-pairs.jsonl \
  --answer-key evaluations/v0.1/test/answer-key.json \
  --out-dir "$OUT/canonical-gold-comparison"

for model in base adapter; do
  python3 scripts/export_context_blind_review.py \
    --prompts evaluations/v0.1/test/prompts.jsonl \
    --manifest evaluations/v0.1/test/manifest.json \
    --pairs "$OUT/canonical-gold-comparison/gold-vs-$model-blind-pairs.jsonl" \
    --out-dir "$OUT/review-$model"
done

# The reviewer ZIP must not include any answer key or audit mapping.
(
  cd "$OUT"
  zip -q -r "BLIND_REVIEW_ONLY.zip" "review-base" "review-adapter"
)
echo "CANONICAL_GOLD_REVIEW_EXPORT_PASS: 20 canonical Gold, 40 blinded pairs"
echo "Audit: $OUT/canonical-gold-audit.json"
echo "Reviewer-only ZIP: $OUT/BLIND_REVIEW_ONLY.zip"
echo "Organizer-only answer keys: $OUT/canonical-gold-comparison/"
