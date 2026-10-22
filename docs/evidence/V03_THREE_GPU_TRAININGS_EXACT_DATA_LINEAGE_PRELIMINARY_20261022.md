# StoryForge v0.1 / R46 / R54 — three GPU SFT dataset lineage audit (2026-10-22)

**Status:** `V01_R54_DIRECT_TARGET_ZERO_CROSSCHECK__R46_R54_PRIOR_SOURCE_REPLAY_14_9_8__FULL_TRIPLE_INPUT_COMPARISON_PENDING__NO_R50`.

This is an aggregate-only, privacy-safe report. No original narrative text, private candidate IDs, account secrets, trainer data or sealed heldout items are included.

## Three actual completed SFT train/validation contracts

| Run | Train | Validation | One-epoch optimizer steps | Data source |
| --- | ---: | ---: | ---: | --- |
| v0.1 baseline | 65 | 15 | 9 | first `data/compiled/v0.3/` (100 Gold selected; separate old Test 20 excluded) |
| R46 v0.2 | 49 | 15 | 7 | R45 frozen source / actual R46 compiled Trainer inputs, exploratory |
| R54 v0.3 | 31 | 9 | 16 | R53 frozen private formal 31/9 release, Owner-authorized |

Summed **145 Train placements + 39 Validation placements** do **not** mean 184 unique examples. The R53 CPU-only 40/40 tokenizer/collator Job, baseline smoke/capacity Jobs, and R55 unit tests are not fourth independent SFT runs.

## Exact final-assistant target SHA256 intersections with R54

| Earlier set | R54 Train 31 | R54 Validation 9 |
| --- | ---: | ---: |
| v0.1 Train 65 | **0** | **0** |
| v0.1 Validation 15 | **0** | **0** |
| R46 Train 49 | **14** | **0** |
| R46 Validation 15 | **9** | **0** |

**New direct check:** Read the genuine Git blob for v0.1 train (`3e64c9932ca43fefa8ecfb200085fe718581b6f9`; 65 JSONL rows) and v0.1 validation (`db0ae8b86038be1b372d547fdb2d6b0b7e33b54e`; 15 rows) through the user's connected GitHub repository. For each record, SHA256 the original final Assistant UTF-8 response; compare against 31 original Train + 9 Validation `target_sha256` values in the Owner-uploaded authentic `R53_HF_CPU40_AUDIT_REPORT_PRIVATE.json`. The four exact intersections are **0/0/0/0**. This is a comparison of identical target strings only, not identical histories or semantically related worlds.

**Previously established R46↔R54:** Original R45/R46 primary export and R53 staged replay previously established **14** R54 Train target repeats from R46 Train, **9** repeats from R46 Validation, **8** nonmatching with either R46 split, and **5** full role/content messages sequences exactly identical across the 23 target repeats. No newly downloaded R46 primary Trainer JSONL was available in this turn; those facts remain attributed to previous primary-source reconciliation and its Owner-side receipt, not mislabeled as fresh read.

Consequently, among R54's 31 Train entries: **14 (45.2%) previously Train targets, 9 (29.0%) previously Validation-only targets, 8 (25.8%) with no exact target match in either previous run** (given independent v0.1↔R54 zero intersections). R46 Validation examples should **never** be described as having received gradients merely because they later became R54 Train.

## Gold195 and v0.1 evidence

Freshly fetched original Git blobs for Gold87 (`a2038e18bee8ddef96b93bb6746270a462f9a6e4`) and Gold108 (`eedb8ff83e6e0629dc2dbc57ee4681fdfde3df90`). Directly compared all 195 target response strings with v0.1 Train65 and Val15: **all four exact target-text intersections 0**. However the Gold87 story UUID set shares **one** exact story UUID with v0.1 Train; Gold108 shares none with v0.1 Train/Val. Therefore target-string independence **does not imply new-world independence**.

R46's R45 49/15 were selected from the subsequent Gold-era candidate process, but a **direct freshly recomputed R46↔v0.1 compiled Trainer input comparison is still required** before asserting a certified count of distinct target hashes across all three actual runs. Do not claim 145 distinct training targets, 184 distinct total entries, or an independent all-world split without that recheck.

## Portable local recomputation tool (NO JOB)

A bounded Python-standard-library-only exact-byte replay package is available as a ChatGPT artifact:
`StoryForge_3_Training_Dataset_Lineage_CPU_20261022.zip`
SHA256 `4ee35999d0fd03a8bfd813a1d79af62cd6e5e2e64db9614888d228ea7845d443`.

Fresh unzipped archive **24/24 synthetic tests PASS**, ZIP CRC + 4 packaged source/docs/test member SHA256 all verified. The ZIP is conversation-delivered, **not** a Git LFS archive or a claim that its Python source is already committed.

- `scripts/r55_three_training_lineage.py`: CLI accepts exact old v0.1 65/15 and original R46 49/15 and R54 31/9 compiled Trainer JSONL; checks all source Git blob SHA1/SHA256 and sizes; computes complete SHA256 pairwise target/input/full-sample overlap and chronological novelty; fails closed if historical R46↔R54 overlap does not reproduce 14/9/8 and 5 complete repeats.
- Optional exact source-inclusive R46 49/15 and R54 31/9 JSONL (all source SHA256 pinned) permits verified **story UUID** comparisons. If either source mapping is missing, output marks story results `NOT_VERIFIED_SOURCE_UUID` and does not infer UUID from sample names.
- `docs/README_THREE_TRAINING_LINEAGE_CN.md`: exact read-only Mac commands to download *existing* R46 `train.jsonl`, `validation.jsonl` and `source-data` files from the original HF Bucket, reuse previously released R54 formal JSONLs and v0.1 tracked Git file, run offline unit tests and compute a local **count-only** receipt. Extra R54 source-inclusive JSONL paths are optional but required for a complete triple-world UUID overlap matrix.
- No new HF GPU/CPU Job, model weight retrieval, inference, training, R50 read or promotion occurred.

Safe aggregate preparation receipt `R55_THREE_TRAINING_LINEAGE_PREP_SAFE_RECEIPT_20261022.json` SHA256 `13ccb96b50c1af7998dd63cf46d1b2de49225f57740184d914a958760ca35663`.

**Next:** Owner executes the read-only CLI against original R46 primary files + locally released R54 files; return just the count-only output JSON (no private stories) to finish the actual first-vs-second overlaps and three-run distinct supervised targets. R50 remains sealed.
