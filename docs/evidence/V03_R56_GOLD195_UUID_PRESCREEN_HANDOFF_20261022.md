# StoryForge R56 — Gold195 historical-exposure prescreen and handoff

Date: 2026-10-22.

**Status:** `R56_GOLD195_UUID_PRESCREEN__24_CANDIDATES_TWO_WORLDS__ALL_FORMAL_HOLD__NO_GPU__R50_SEALED`.

Owner chose **24 proposed questions across ideally 4 genuinely independent story worlds with 3 independent reviewers**, rather than the prior 60-question design. The first historical-exposure screen examined frozen Gold87 (87 rows), Gold108 (108 rows), v0.1 train/validation/test (65/15/20), and source-grounded historical R46 49/15 and R54 31/9 splits. It compared story UUID and target SHA records. These checks find:

- Gold195: 195 unique frozen target SHA256, 13 represented world UUIDs.
- **11 world UUIDs / 163 Gold rows** had known overlap with previous training, validation or previous v0.1 testing worlds.
- **2 world UUIDs / 32 Gold rows** had no **observed exact UUID** overlap: story 03 has 14 Gold rows; story 05 has 18.
- A deterministic nonquality preselection chose 12 rows from each of story 03 and story 05, totaling **24 provisional HOLD candidates**, but only **2 worlds**, leaving a **2-world shortfall** against the Owner's 4-world design.
- **Formally admitted fresh independent evaluation questions: 0**.

**Strict boundary:** UUID/hash non-overlap is not proof of semantic/story-world independence or lack of prior evaluation exposure. Target-time canon, exact model-visible history, content/age/consent/player agency, cross-world characters/aliases, and prior semantic exposure require new independent checks. These 24 must not be called certified heldout, nor used for automatic R54 promotion. Existing R55: R54 12:8 majority wins but six-dimension means R46 3.3972 > R54 3.2750; R54 remains NOT_PROMOTED. R50 remains sealed. No new paid inference/training has been authorized.

Offline handoff artifacts prepared in ChatGPT's conversation: `StoryForge_R56_New_Conversation_Handoff_SAFE_20261022.zip` (comprehensive count-only handoff), `StoryForge_R56_Gold195_Screening_NoGPU_20261022.zip` (separate **private** source exposure metadata and executable CPU-only screening), `R56_GOLD195_PRELIMINARY_ELIGIBILITY_AUDIT_20261022.json` (count-only). The R56 source screening script's offline suite **11/11 tests PASS**, not equivalent to Owner-Mac end-to-end original-source replay. Avoid uploading private source UUIDs or raw candidate IDs into this evidence file.

**Next:** Owner Mac replays the source-pinned offline R56 script against actual Git blobs and historical exposure manifest; reviewers independently assess story 03/05 HOLD candidates. Separately obtain and attest two genuinely unexposed story worlds or explicitly downgrade to a 2-world **development exploratory** set. Do not touch R50 or schedule a new GPU Job.
