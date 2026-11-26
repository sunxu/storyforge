# R51 Gold195 — actual source inventory results and next admissible work

Date: 2026-10-19. **No GPU, no training approval.**

The mainline was deliberately switched from indefinitely repeated R50 W17
semantic reviews into this separate R51 branch. R50 Draft PR #2 and ten
frozen W17 held-out cases remain unchanged under `SEMANTIC_HOLD`.

## Verified on actual frozen repository inputs

R51 dedicated CI https://github.com/sunxu/storyforge/actions/runs/39220232578
was SUCCESS using real Gold87 and Gold108 records (not synthetic
fixtures only). Original Git blobs were pinned and checked.

- **195 original rows**: 87 + 108; 195 unique candidate IDs.
- **195/195 final Assistant target hashes match original bytes**:
  Gold87 87/87 metadata target digests; Gold108 108/108 frozen index.
- Gold108 had **3 original target-digest gaps**; their digests were
  recovered from the *byte-pinned independent review index*.
- Gold108 had **15 missing directly mappable story-number fields**;
  all 15 map through that review index to the expected numeric worlds.
- **Three Gold108 original story IDs are missing in BOTH the record and
  the review index**. These remain `SOURCE_STORY_ID_HOLD`. The index's
  number and the neighboring records of that world are not substitutes
  for an independently verified source-story ID.
- 13 distinct source-story IDs found from the other records; numeric
  01–15 groups cover 13 represented stories (07 and 11 have 0 Gold).
- 108 indexed double ACCEPT entries; content-quality signoff only.
- **923 historical Assistant message occurrences** in Gold195 windows
  must be masked as unsupervised (some message texts may appear in
  multiple windows). A declarative mask contract is NOT actual
  `ms-swift` collator output.
- 0 formally admitted training rows, 0 Train/Validation assignments.

This does not grant age/rights/story-time card/long-term instruction/
player-agency/world-isolation approval. R45's 18 HOLD remain unchanged.

## Execution priorities — actual quality gain, not more W17 audit loops

**A. Source repair (3 rows).** Retrieve authenticated original source
archive and versioned manifest for the three unresolved Gold108
records; reconcile source story/session and target message UUID against
the canonical, SHA-pinned export. Keep those rows HOLD if the source
cannot be obtained; do not overwrite original Gold or fabricate UUIDs.

**B. Gold195 per-row review (up to 192 identifiable rows).** Produce a
PRIVATE, source-anchored triage sheet for canonical target-time card,
full source history, long-term constraints, player agency, rights/age,
provenance, and independent quality reviewers. Explicitly include
PASS/HOLD/REJECT and source pointers for every gate. A/B curator
acceptance only establishes the existing quality-selection event.

**C. Whole-world component split.** Resolve known linked worlds and
v0.1 historical overlap BEFORE choosing Train/Validation; do not
split based on random row shuffling, row count quota, raw UUID equality
or a single repeated token.

**D. Actual CPU label-mask gate.** Once a provisional data-only
candidate set is reviewed and source-safe, run real pinned ms-swift
collator to confirm only final Assistant supervised and all 923
historical Assistant window occurrences ignored, with no source-target
leakage, no 16384-token overflow and no silent truncation.

**E. Preregister v0.3-A data-only experiment.** R52 and R53 advance
only after per-row R51 quality/source admission. R54 paid GPU is not
authorized; training and R56 still respect the separate R50 test gate.

The goal is a defensible increase over the old R45 49 Train / 15 Val
experiment, ideally 120–160 *eligible* Gold rows if the actual source
allows, never an artificial acceptance quota. Current true admission
is **0**; neither Gold195 nor 192 source-identifiable rows are
currently a training-approved corpus.

**Gate:** `R51_GOLD195_TARGET_BYTES_RECONCILED_195_195 ·
3_SOURCE_IDENTITIES_HOLD · 923_HISTORY_ASSISTANTS_MASK_PENDING ·
PER_ROW_TRAINING_ADMISSION_HOLD · NO_GPU`.
