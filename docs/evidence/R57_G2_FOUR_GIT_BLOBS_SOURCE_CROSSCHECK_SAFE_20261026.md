# StoryForge R57 G2 — four frozen Git blobs read-only source crosscheck (SAFE)

**Date:** 2026-10-26 (Asia/Singapore). **Evidence tier:** direct, authenticated GitHub-connected `git blob` text read of four pinned archive files; in-memory exact-string comparison and aggregate-only output. This is **not** a private eight-source SFT audit, an independent byte-level Trainer file reconstruction, a R50 evaluation, or a Dataset v0.4 admission result.

## Four-source identities and counts

| Group | Frozen Git Blob SHA-1 | Records | Distinct final Assistant texts | Distinct story UUIDs |
|---|---|---:|---:|---:|
| GOLD87 | `a2038e18bee8ddef96b93bb6746270a462f9a6e4` | 87 | 87 | 5 |
| GOLD108 | `eedb8ff83e6e0629dc2dbc57ee4681fdfde3df90` | 108 | 108 | 8 |
| V01_TRAIN | `3e64c9932ca43fefa8ecfb200085fe718581b6f9` | 65 | 65 | 15 |
| V01_VALIDATION | `db0ae8b86038be1b372d547fdb2d6b0b7e33b54e` | 15 | 15 | 2 |

Each source's final message was Assistant, preceded by User; all 275 rows had valid suffixes. Gold87+Gold108: 195 unique verbatim final targets, 13 distinct observed story UUIDs with no cross-batch exact UUID overlap. V01 Train65/Val15 have no exact target repeat or exact UUID intersection.

**Primary-source schema discovery:** All 87 Gold87 rows have `metadata.story_id` and `metadata.target_sha256_utf8`. In Gold108, 105 rows have `metadata.story_id` + `metadata.target_sha256`; another 3 have `metadata.source_story_id` + `metadata.target_content_sha256`. Those 3 alternate-format rows all map to **one already represented Gold108 story UUID**. A `story_id`-only parser would falsely report 3 missing worlds. In total all 108 Gold108 rows carry one supported source-world key and one known target-hash key. This is a **metadata-field reconciliation**, not proof that historical string hashes have been independently recalculated or signed.

## Pairwise comparisons (all exact, no fuzziness)

All six unordered pairs of the four groups have **0 exact final Assistant text matches**, **0 exact role/content full-sequence matches**, and **0 exact role/content preceding-history matches**. Comparisons ignore non-role/content message keys such as `loss` and use exact serialized strings; they do not prove absence of truncated, semantically repeated or alias-connected passages.

**Exact story UUID intersections:**
- GOLD87 ↔ V01_TRAIN: **1** shared UUID (so target-string independence does **not** mean world independence).
- Other five source-pair UUID intersections: **0**.

The Gold87 and Gold108 `training_admission` metadata values are **all** `PENDING_NOT_APPROVED` (87+108), not Dataset v0.4 ACCEPT. Historical quality curation is not an admission grant.

## Data-integrity / privacy limitations

- Compared the exact readable GitHub blob JSONL content in-process but did **not** independently recompute SHA-1 of the returned bytes or per-row SHA256 targets in this audit. Git Blob IDs are pinned provenance, not evidence of new independent cryptographic byte verification.
- World alias graph is **not** signed; UUID equality cannot certify world-component independence.
- This scoped replay includes neither R46 49/15 nor R54 31/9, so the historical R46↔R54 14/9/8 result remains **previously reported**, not independently newly replayed.
- No narratives, actual story UUIDs, private sample IDs, original target hash lists or protected evaluation items are in this receipt. No R50 read. No GPU, HF CPU, inference, training, promotion or admission.

**State:** `R57_G2_FOUR_GIT_BLOBS_AGGREGATE_CROSSCHECK_PASS__GOLD108_MIXED_FIELDS_DOCUMENTED__FULL_EIGHT_SOURCE_AND_WORLD_ALIAS_GATES_HOLD`.
