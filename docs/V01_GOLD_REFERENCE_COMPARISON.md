# StoryForge v0.1 — Original Gold Reference Comparison

**Status: CPU PREPARATION READY / HUMAN REVIEW NOT RUN**

Scope: retrospective comparison of the *same 20 already evaluated story-held-out samples* with their original selected Gold assistant replies. This is **not** v0.2, not a new unseen test set, and does not change the frozen Base-vs-Adapter decision.

## Questions

1. How do the original Base and v0.1 Adapter outputs compare against the original selected Gold for identical prompts?
2. Which dimensions differ: story continuity, character consistency, instruction adherence, literary quality, interactive progression, player agency, and world facts?
3. Does the original Gold itself contain mistakes? Gold is a **reference**, not an unquestionable ground truth.

Historical Base-vs-Adapter scores and arbitration are unchanged. Gold-relative win rates from distinct reviews cannot simply be subtracted to infer Adapter-vs-Base wins; the direct Base-vs-Adapter reviews remain primary for that decision.

## Sources and fail-closed alignment

- Original Gold targets: local data/compiled/v0.3/test.jsonl (the existing, gitignored compiled 20-item Test, **not stored in this repository**).
- Frozen prompts: evaluations/v0.1/test/prompts.jsonl.
- Frozen SHA256 manifest: evaluations/v0.1/test/manifest.json.
- Frozen Base/Adapter responses: evaluations/v0.1/test/blind-pairs.jsonl.
- Frozen A/B answer mapping: evaluations/v0.1/test/answer-key.json.

scripts/prepare_gold_comparisons.py checks all five sources, exact prompt content, SHA256, sample ID, source line, and the original A/B identity. It refuses mismatched samples and a preexisting output directory. All historical source files are read-only. The output answer mapping is kept in separate files.

## CPU-only workflow (no HF Job)

Run on the Mac where the original compiled Dataset v0.3 Test file exists:

~~~bash
cd storyforge
git pull --ff-only origin main
python3 -m pytest -q tests/test_prepare_gold_comparisons.py

python3 scripts/prepare_gold_comparisons.py \
  --compiled-test data/compiled/v0.3/test.jsonl \
  --prompts evaluations/v0.1/test/prompts.jsonl \
  --manifest evaluations/v0.1/test/manifest.json \
  --blind-pairs evaluations/v0.1/test/blind-pairs.jsonl \
  --answer-key evaluations/v0.1/test/answer-key.json \
  --out-dir /tmp/storyforge-v01-gold-comparison

for model in base adapter; do
  python3 scripts/export_context_blind_review.py \
    --prompts evaluations/v0.1/test/prompts.jsonl \
    --manifest evaluations/v0.1/test/manifest.json \
    --pairs "/tmp/storyforge-v01-gold-comparison/gold-vs-${model}-blind-pairs.jsonl" \
    --out-dir "/tmp/storyforge-v01-gold-comparison/review-${model}"
done
~~~

Expected success marker: GOLD_COMPARISON_PREP_PASS: 20 source samples, 40 blind pairs.

The output directory holds:
- gold-vs-base-blind-pairs.jsonl — 20 cases.
- gold-vs-adapter-blind-pairs.jsonl — 20 cases.
- gold-vs-base-answer-key.json / gold-vs-adapter-answer-key.json — **never expose to blind reviewers**.
- audit.json — input file hashes and source-alignment status, explicitly *not* a grading result.
- review-base/ and review-adapter/ — existing context-enriched Chinese reviewer CSV formats.

## Review and reporting

- Blindly score the 40 A/B comparisons using the existing five quality dimensions (1–5), overall preference A/B/TIE, detailed reason, and serious issue record.
- Separately flag PLAYER_AGENCY, CHARACTER_FACT, WORLD_FACT, TIMELINE, UNSUPPORTED_EVENT, and GOLD_ISSUE.
- Do not reward Gold automatically, nor use BLEU/ROUGE/textual similarity as the primary score; interactive fiction can have multiple valid continuations.
- Keep any existing reviewer scores/annotations intact. Do not retroactively rewrite historical evidence or change v0.1-evidence-frozen.
- Unblind **after** new reviews finish; report Gold wins/model wins/ties, per-dimension differences, notable improvements and regressions, disputed items, and reviewer uncertainty.
- The already disclosed 20 prompts provide diagnostic evidence, not independent generalization. Gold agreement does not establish absolute model quality.

**No new inference, training, GPU use, checkpoint download or change to the original 20 test items is required.**
