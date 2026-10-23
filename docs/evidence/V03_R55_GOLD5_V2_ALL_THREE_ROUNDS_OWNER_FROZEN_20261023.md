# StoryForge R55 Gold5 v2 — Three blinded rounds frozen (Owner-local evidence)

Date: 2026-10-23 (Asia/Singapore). Evidence tier: owner-pasted local terminal status and count-only JSON, **not** independent rehash of private CSV bytes. These are 20 reused R47/R48/R55 development cases from two historically exposed story worlds; not new R50 Held-out.

## Owner-reported structural gates

| Round | Status | Rating cells | Rows with at least one candidate problem flag |
|---|---|---:|---:|
| Pair (v0.3-A versus v0.2) | `R55_GOLD5_V2_PAIR_3_REVIEWERS_FROZEN__KEY_NOT_READ__NO_R50` | 720/720 | 32/60 |
| Four (four models) | `R55_GOLD5_V2_FOUR_3_REVIEWERS_FROZEN__KEY_NOT_READ__NO_R50` | 1440/1440 | 50/60 |
| Five (four models + original Gold reference) | `R55_GOLD5_V2_FIVE_3_REVIEWERS_FROZEN__KEY_NOT_READ__NO_R50` | 1800/1800 | 50/60 |

- Nine completed scored CSV hashes were reported, three per round. Latest Five SHA256s: Reviewer01 `3ac83edc576c3c2fa2956b2ea4e611bb6ae9772bf074a50de91418c579e48606`, Reviewer02 `9e47b51167ad8b45b6a844e612d6acd42ef4574022a711961ce2095a60ec8be4`, Reviewer03 `b6bca635c9bded309b1234989d7f59cecb5ec4dc22b555c678afdc5610c44bfe`.
- All three receipts reference the same v2 preparation receipt SHA256: `6476da25e7d6b043a7bec3d413bfc75885c8571c188f318e3a4eb523888bdaa4`.
- Explicit unchanged boundaries: `unblinding_performed=false`, `r50_accessed=false`, `gpu_job=false`, `model_promotion=false`; R50 remains out of scope.
- Flag counts denote Reviewer-by-case *presence* of one or more unadjudicated marks, not proven unique errors, hard failures, or attribution to any unblinded model.
- Reviewer intellectual independence, semantic accuracy and age/source rule correctness are not established by CSV integrity alone.

## Owner-only next phase

A no-job, pure-stdlib post-freeze validation/unblinding implementation is prepared as `StoryForge_R55_GOLD5_V2_OWNER_UNBLIND_NOJOB_20261023.patch` (not yet run on real private data), SHA256 `656d4e37f3d5398096abb838fc115cf2fbbfe4e5dd544b3c9f8d384885919b2c`; companion ZIP SHA256 `65b040dec18d2b2c5ecd45e22b32d2c9e916ecc4a1b7033d5408442ae9bb67e5`. Synthetic tests 17/17 PASS and fresh synthetic Git patch application/tests PASS.

1. Owner invokes **verify** mode to validate all three receipts, nine frozen private files, pristine rows and Owner-supplied hashes, without reading the coordinator key.
2. Only if all checks PASS, Owner invokes **unblind** mode in new local private output directory. The tool then validates key SHA and response mapping to frozen anonymous content before deriving separate Pair, Four, Five preferences/ratings/flag summaries.
3. The summary may be provided to assistant after redaction checks; private case-level mapping remains Owner-only. Case/event-based severe problems require later adjudication, and all R55 conclusions remain development-only. R54 previously declared NO-GO for spending protected R50 remains unchanged until new interpreted evidence supports reconsideration.

Status: `R55_GOLD5_V2_3_ROUNDS_OWNER_FROZEN_REPORTED_PASS__UNBLIND_PREPARED_NOT_RUN__R50_UNTOUCHED__NO_PROMOTION`.
