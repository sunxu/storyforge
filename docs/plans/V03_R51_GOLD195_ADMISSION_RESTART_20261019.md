# R51 — Gold195 real-source admission triage (no training approval)

**Owner direction 2026-10-19:** shift the primary StoryForge effort from
repeated W17 R50 alias audits to R51 training-data curation and evidence.
W17's ten cases remain frozen on the separate Draft R50 branch, under
SEMANTIC_HOLD. This R51 work is independent of R50 final sealing.

## Inputs and intended decisions

Two Git-tracked, byte-frozen original Gold cohorts:

- 87 source records in `evaluations/v0.2/gold-quality-87/`;
- 108 source records in `evaluations/v0.2/gold-quality-108/`.

Both were accepted for curator **CONTENT QUALITY**, not training.
These records must never be rewritten or merged into an unreviewed
`train.jsonl`. R45's 18 HOLD cases remain HOLD with no automatic release.

### Phase 1: objective preflight, no model calls

Run `python3 scripts/v03_r51_gold195_source_inventory.py --repo .`.
The script checks the real 87+108 Git blob SHA1 pins, candidate IDs,
source story IDs, final Assistant target, recorded source-target SHA256,
declared mask contract, source-message indices, training and split status,
and provides **only aggregate** story-number/coverage stats.

This step does NOT assert that:
- actual `ms-swift` collator labels are verified;
- historical card content was active before each target;
- quality reviewers certified source rights/ages/player agency/long-term constraints;
- story aliases or train/val/old v0.1 Test are disjoint;
- any new R50 cases are cleared as a sealed evaluation set.

Never print prompts or target text to CI logs. All failures stop the
training-admission path; the original 195 lines remain untouched.

### Phase 2: R51 decisions after the preflight

Apply strict, source-anchored per-record gates:
`SOURCE_AUTHORITY`, `CARD_AS_OF_TARGET`, `FULL_HISTORY`,
`PLAYER_AGENCY`, `LONG_TERM_CONSTRAINT`, `AGE_RIGHTS`,
`FINAL_ASSISTANT_LABEL_MASK`, `WORLD_COMPONENT_SPLIT`,
`PREVIOUS_TEST_EXPOSURE`, `INDEPENDENT_2_REVIEWERS`.

Classify each record as `PASS`, `HOLD` or `REJECT` with
private evidence pointers. The original Gold quality decision does
not automatically set any gate to PASS. Preserve R45's previous 18 HOLD.

Try for ~120–160 admitted records only if source proof truly permits;
this is not a mandatory target. Split by verified **world components**
rather than arbitrary row count. A 49/15 experimental baseline remains
historical reference and does not become a production-admitted set.

### Scope and chronology

Phase R51 depends on R49 but may proceed **in parallel** with R50 HOLD.
Do not launch HF/GPU work. R52 experiment preregistration depends on
R51; R53 CPU collator admission depends on R50 and R52; R54 GPU
requires a separate explicit owner authorization.

**Current gate: `R51_GOLD195_SOURCE_TRIAGE_PENDING · TRAINING_ADMISSION_HOLD · NO_GPU`.**
