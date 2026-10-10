# StoryForge v0.1 — Original Gold Reference Comparison

**Status: CANONICAL_GOLD_MATCH_PASS / BLIND_REVIEW_READY / FORMAL_HUMAN_REVIEW_PENDING**


## Canonical Gold verified from final Dataset v0.3 Test (2026-10-10)

**PASS.** The project owner supplied the full, compiled `test(1).jsonl` (20 records); the final assistant content for all 20 records matches the earlier candidate Gold text **byte-for-byte at the Unicode text level**. Each prompt reconstructed from all messages preceding the final assistant matched the frozen `manifest.json` SHA256, sample ID, and source line (**20/20**). The historical Base/Adapter outputs were also reconciled (**40 model responses**); original model strings retain their empty leading think wrapper.

- Official uploaded compiled Test SHA256: `d8eee6db5882d85dce7ffc01256e7c5b9b46e133bdb2cf8591259112b92e980d`.
- Frozen v0.1 Test manifest SHA256 (source copy): `2f0e4104262541f598084e8ba3c4eef520b74f825ec24b78ca61c4b5630379e6`.
- Previously supplied candidate-source ZIP SHA256: `9e9dd36ef0ede813c0a22d2d44c43b4d1ccc656fcd9fbe0943a0b860aede733f`.
- Counts: **20/20 prompt-manifest PASS**, **20/20 candidate-vs-canonical Gold PASS**, **40/40 model response body reconciliation PASS**.
- Machine-readable evidence summary: [`docs/evidence/V01_GOLD_CANONICAL_RECONCILIATION_20261010.json`](evidence/V01_GOLD_CANONICAL_RECONCILIATION_20261010.json).
- Official Gold-vs-Base and Gold-vs-Adapter reviewer-only ZIP (two separate 20-case CSVs) and organizer-only provenance/answer-key ZIP were produced in the current conversation workspace; intentionally not added to the immutable v0.1 historical tree.

**Research-only observation, NOT blind scores:** A single known-identity qualitative reading provisionally favored Gold over Base in 13 cases, Base in 2 and considered 5 equivocal; Gold over Adapter in 14, Adapter in 2 and considered 4 equivocal. Gold has its own notable agency/instruction violations, and these **must not** be used as a formal promotion metric or compared as if 40 cases were independent. The fresh anonymous reviewer CSVs are blank and await grading. Existing two-round Base-vs-Adapter conclusions remain unchanged.

The older "PENDING" paragraphs below document the **historical pre-upload state**, superseded by this verified addendum. Do not rerun training, inference or earlier reviews to close this data provenance gate.

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


## 2026-10-10 CPU source-provenance triage (partial; no quality grades)

The local uploaded authoring workbook `Qwen_互动剧情_100条训练Schema.xlsx` was inspected against a 20-case existing held-out reviewer CSV (`StoryForge_Reviewer_01(9).csv`), its saved original answer key and 20-entry test manifest:

- **20/20 unique current-user-input matches** to workbook `训练主数据`; the workbook covers the two original held-out story groups.
- **11/20 candidate Gold responses** were also found **verbatim as complete text** inside other archived held-out prompts' previous dialogue (stronger independent provenance evidence).
- **9/20 candidate Gold responses** have *only* unique-user-input matches. Those do **not** establish equality with the final compiled Dataset v0.3 Gold targets.
- Workbook rows have `context_complete=NO`, `sft_ready=PENDING_DB_BACKFILL` and unfilled source record IDs. This early authoring schema must **not** silently replace the final `data/compiled/v0.3/test.jsonl`.
- A 40-response archive consistency check matched all original Base/Adapter A/B text fields against the frozen `evaluations/v0.1/test/blind-pairs.jsonl` using independent FNV-1a 64-bit UTF-16-code-unit digests. This is a consistency check, not a proof of canonical Gold equality.
- Two **candidate-Gold** blinded 20-case reviewer sheets, with their answer key kept separately, were produced locally for inspection; the unverified candidate Gold text and new reviewer sheets were **not committed**.
- **Gate: `PARTIAL_SOURCE_PROVENANCE / BLIND_SHEETS_READY / QUALITY_REVIEW_NOT_RUN`.** No Gold-vs-Base or Gold-vs-Adapter win totals or quality gains have yet been established.

**Next required gate:** run the already committed `scripts/prepare_gold_comparisons.py` with the canonical compiled `data/compiled/v0.3/test.jsonl` against frozen `prompts.jsonl`, `manifest.json`, `blind-pairs.jsonl` and `answer-key.json`. That script fails closed on any mismatch and prepares definitive blind materials without new GPU inference. Compare any candidate-Gold workbook text against those canonical Gold targets before considering the local candidate sheets final.

The immutable `v0.1-evidence-frozen` tag and prior v0.1 review results remain untouched.


## Canonical Gold reconciliation gate (2026-10-10, CPU only)

The 2026-09-30 authoring workbook was linked to all 20 frozen held-out current-user inputs. However, its candidate Gold is not the canonical compiled Test: 11/20 have verbatim support in other frozen dialogue history, while 9/20 have only uniquely matching user input. **All 20 must be checked against the actual** `data/compiled/v0.3/test.jsonl`. In particular, constructing a new `test.jsonl` from the workbook is not acceptable evidence.

The separate, earlier organizer audit ZIP contains `TRIPLETS_INTERNAL_UNBLINDED.json`. Keep it away from blind reviewers. The new `scripts/audit_gold_reference.py` compares candidate Gold to canonical Gold by frozen SHA256 prompt, source line and sample ID, reporting exact UTF-8 Gold SHA256 per sample. It leaves mismatches visible and refuses to claim a pass.

~~~bash
cd storyforge
git pull --ff-only origin main
python3 -m pytest -q tests/test_audit_gold_reference.py

# Download the organizer-only candidate source package from this chat, then:
mkdir -p /tmp/storyforge-v01-gold-organizer
unzip -n StoryForge_v01_Gold_候选来源校验输入_仅组织者.zip -d /tmp/storyforge-v01-gold-organizer
find /tmp/storyforge-v01-gold-organizer -name TRIPLETS_INTERNAL_UNBLINDED.json

# Supply the actual resulting path from the find command as --candidate.
python3 scripts/audit_gold_reference.py \
  --compiled-test data/compiled/v0.3/test.jsonl \
  --prompts evaluations/v0.1/test/prompts.jsonl \
  --manifest evaluations/v0.1/test/manifest.json \
  --candidate /tmp/storyforge-v01-gold-organizer/TRIPLETS_INTERNAL_UNBLINDED.json \
  --output /tmp/storyforge-v01-canonical-gold-audit.json
~~~

If the ZIP extracts to a nested directory, use that path rather than guessing. Success is **`CANONICAL_GOLD_MATCH_PASS: 20/20 matched`**. On 1–19 matches, the script writes a diagnostic JSON and exits status 2 with `CANONICAL_GOLD_MISMATCH__REBUILD_REVIEW_SHEETS`: do **not** reuse the old candidate review sheets.

After a successful canonical audit, run the existing `scripts/prepare_gold_comparisons.py` command above, which produces two new 20-case blind datasets **from the actual compiled Gold** and the frozen Base/Adapter responses. Run `export_context_blind_review.py` to produce reviewer CSV files and check that no answer-key JSON is included in reviewer handoffs. The old candidate sheets were not frozen or scored.

**Gate status at document creation:** `CANONICAL_TEST_JSONL_NOT_ACCESSIBLE_IN_CURRENT_SESSION`, exact equality **PENDING**, no Gold-based quality winner claimed; no Job and no GPU usage.


### Candidate organizer package and normalization audit

The earlier organizer provenance ZIP lacked the 20 candidate Gold texts. A distinct organizer-only archive, `StoryForge_v01_Gold_候选来源校验输入_仅组织者.zip`, now includes `TRIPLETS_INTERNAL_UNBLINDED.json` and a README; SHA256 of that ZIP is `9e9dd36ef0ede813c0a22d2d44c43b4d1ccc656fcd9fbe0943a0b860aede733f`. This is supplied separately to the project owner, **not** stored among frozen GitHub evidence.

Cross-check of the earlier *candidate* blind sheets and this new organizer source:
- Gold: 20/20 identical candidate replies in **each** of Gold-vs-Base and Gold-vs-Adapter sheets.
- Model bodies: Base 20/20 and Adapter 20/20 equal to organizer triplets **after stripping only the empty leading `<think>\n\n</think>\n\n` wrapper** that occurs in the archived blind-model outputs. Raw review-sheet replies retain the original wrapper; no substantive story text was altered.
- These tests protect the **candidate material's internal alignment**, not the candidate-vs-canonical Gold provenance. The canonical Gold gate is still **PENDING** until the final compiled `test.jsonl` is available.


### Recommended one-command workflow on the original Mac

The simplest CPU-only path is the fail-closed wrapper script, which executes canonical Gold provenance audit **before** exporting either 20-case blind review sheet. The generated reviewer ZIP excludes answer keys.

~~~bash
cd storyforge
git pull --ff-only origin main

bash scripts/run_v01_gold_canonical.sh \
  "$HOME/Downloads/StoryForge_v01_Gold_候选来源校验输入_仅组织者.zip" \
  "$PWD/data/compiled/v0.3/test.jsonl" \
  "/tmp/storyforge-v01-gold-final"
~~~

The output directory **must not exist** before execution. If Gold differs, the audit JSON remains in the new directory with each candidate and canonical Gold SHA256; the script exits before creating reviewer CSVs. If every candidate Gold is identical to canonical, the expected terminal marker is:

~~~text
CANONICAL_GOLD_MATCH_PASS: 20/20 matched
GOLD_COMPARISON_PREP_PASS: 20 source samples, 40 blind pairs
CANONICAL_GOLD_REVIEW_EXPORT_PASS: 20 canonical Gold, 40 blinded pairs
~~~

Outputs: \`/tmp/storyforge-v01-gold-final/canonical-gold-audit.json\` (source audit), \`BLIND_REVIEW_ONLY.zip\` (two sets of reviewer CSVs without answer maps), \`canonical-gold-comparison/\` (organizer-only paired results and answer keys). Do not treat any of these as *review scores* until human ratings are completed.

