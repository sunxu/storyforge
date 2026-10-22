# StoryForge R56 — Story 03/05 original-source replay (CPU-only, 2026-10-22)

**Status:** `SOURCE_FILES_SHA256_AND_32_CASES_REPLAY_PASS__TIMEPOINT_AND_SEMANTIC_GATES_HOLD`.

## Verified directly against Owner-uploaded full JSONL originals
- **2/2 source files:** full-file SHA256 exactly match frozen Gold87 source references.
- **9,462 original messages:** slot 03 = 5,318; slot 05 = 4,144.
- **32/32 cases:** target and each frozen predecessor source message **ID / role / turn / full content / array index / order / completed status** match original source; target text SHA256 and frozen-history SHA256 reverified.
- Original sources are single-line JSON objects containing complete `messages` arrays. The second source has 4 turn gaps totaling 8 absent turn numbers; **none** falls inside the 32 selected review windows. Therefore source-turn arithmetic must not substitute for exact source message IDs.
- P0 source findings **3/3 examined**: a duplicated user source message was later than its Gold target (not a lost pre-target message); a separately preserved raw input contains a visibly unfinished world-setting sentence; several near-name character identities require case-specific mapping, with one explicit below-18 age field in a **posthoc** export card. No assumption about the target-time ages or relationship is justified by the later snapshot.
- Original source modifications: **0**; Gold edits: **0**.

## Hard holds (unchanged)
- Historical model-visible System Prompt, runtime memory and exact target-time card versions: **not certified**.
- One below-18 age value in the posthoc exported story card conflicts with global adult Owner attestation; case-specific age/consent at each target remains **HOLD**, not auto-failed nor auto-approved.
- Historical semantic train/development exposure: **HOLD**; shared-world and aliases: **HOLD**.
- All 32 review cases **HOLD**; 24 provisional selections **HOLD**; formal independent Held-out admission **0**.
- Extra independent worlds required: **2**. Any 2-world-only evaluation is exploratory development, not 4-world Held-out.
- R50 not accessed; no GPU, training, inference or model promotion.

## Deliverable boundary
Private case-to-source SHA mappings, source message IDs, character names/ages and reviewer rationale exist only in the Owner-private evidence bundle. **No private novel text, candidate IDs, source IDs, character names or world-relationship secrets are committed here.** The new CPU-only tamper-resistant replay script passed **14/14 synthetic tests**. This record is count-only; source contents do not enter ordinary Git.

**Final gate:** `SOURCE_EXACT_REPLAY_PASS__OFFICIAL_TEST_ADMITTED_0__TARGET_TIME_SEMANTIC_HOLD`.
