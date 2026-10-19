# StoryForge R51 — move Gold195 toward a usable v0.3-A training cohort

**2026-10-19 actual execution:** R51 isolated GitHub CI `39233810359`
passed the **real** frozen Gold87+108 source-byte/target-digest/review-index
preflight. No newly approved Train/Val exists.

## Material verified

- 195 untouched quality-selected records; 195 unique original Assistant targets
  with correct target SHA256; 1,909 source history message entries (3–12 per row).
- Thirteen nonempty source-story ranks / 13 distinct source-story IDs in
  the two cohorts. Do **not** infer that distinct IDs guarantee semantic
  world independence or disconnected character aliases.
- 3 of the 108 rows use `source_story_id` instead of `story_id`;
  the original 108 uses three different target-digest metadata fields.
  These are supported **as-is** without backfilling or changing any source
  JSONL rows.
- 171 rows explicitly carry an export-card or target-card
  `UNVERIFIED`-like flag; 22 rows lack both examined direct source
  index metadata fields; 10 Gold87 rows mark source character age as
  `UNSPECIFIED`. **Flags are potentially overlapping**, and the other
  24 rows cannot automatically be treated as certified cards.
- Every record remains `training_admission=PENDING_NOT_APPROVED` and
  `split=null`. The new source-integrity PASS is not an ethical/content,
  timeline, permission, card, world-isolation, tokenizer or collator PASS.

## Bounded next R51 work: source-context-only vs card-dependent

Instead of attempting to recover 171 full historical platform runtime-card
requests by default, classify each row in a **private source-anchored**
review as one of:

1. `CONTEXT_ONLY_POSSIBLE__HOLD`: complete original contiguous chat
   history and explicitly sourced long-term constraints would make
   a usable, truthful input **without importing unverified posthoc card**.
   This is a **proposal**, not training acceptance. It still needs
   age/consent/rights, future fact leakage, player agency and story-level
   validation.
2. `CARD_OR_LONG_RANGE_SOURCE_REQUIRED__HOLD`: the target behavior
   depends on a card fact, hidden relationship or earlier rule absent
   from supplied context. Do not silently invent that rule, prepend
   the export-time card as if historically available, or shorten the
   context while claiming long-range fidelity.
3. `CONTENT_OR_RIGHTS_HOLD`: missing evidence for age/consent, rights,
   disallowed target behavior or reviewer disagreement. The ten explicit
   age-unknown story 04 cases require dedicated source verification.
4. `SOURCE_POINTER_RECONCILIATION_HOLD`: a source index field is absent
   in the original metadata; reconcile against authenticated frozen
   exports, not a guessed message number or direct assignment from
   unrelated testimony.

Cases may carry multiple flags. After the original, source-anchored
review and rights/agency gates, store **a new private versioned approval
workpaper** with row ID, source target SHA, explicit missing evidence,
card-dependency decision, reviewer citations, permissible deployment-input
contract, and STOP/HOLD or recommendation. Never mutate Gold195 originals.

## Training/validation pathway

Only after a real reviewer records admissible world components should
we propose a story-component-disjoint Train/Validation split. v0.1 exposed
test and frozen R50 new test worlds remain non-training, and R45 HOLD18
are never silently reused. Where the verified admissible pool is smaller
than the planned 120–160, report the actual count; do not force samples
to meet the quota.

R52 should preregister a **data-only v0.3-A** SFT experiment with
the existing Qwen/Qwen3.8-27B revision, training configuration and
System Prompt, except for explicitly declared data changes. R53
requires actual CPU tokenizer and collator mask verification; no R54
paid GPU without a separate owner instruction and all mandatory gates.

### Stopping unnecessary audit

Do not reconstruct historical runtime card/long-term-rule inputs for
rows which can be validly trained from **verifiable local chat context
alone** and whose reviewer confirms the proposed context-only contract.
Conversely, if an output needs external card information, a local
context-only downgrade is NOT an excuse to invent that fact. A single
source-anchored review should decide each route and document why.

**Present state:** `R51_GOLD195_ORIGINAL_INTEGRITY_PASS ·
R51_ADMISSION_ZERO · TRAIN_VAL_NOT_SPLIT · R50_W17_EVIDENCE_HOLD · NO_GPU`.
