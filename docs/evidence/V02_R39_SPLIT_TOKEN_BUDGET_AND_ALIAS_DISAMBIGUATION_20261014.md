# StoryForge v0.2 — R39 training readiness: split-token evidence and scoped alias correction

Date: **2026-10-14**. **Training admission remains `PENDING_NOT_APPROVED`; GPU has not been started.** Historical curator Gold 195 and R27's frozen 117-row derivative are unchanged; the filtered 82-row review ceiling is identical to R37.

## Substantive findings

1. **Prior alias false positive resolved only within this exact lexical scope.** The R37 probe flagged “绵绵” across five stories. R39 inspected **all 26 actual substring occurrences** within 82 R27-visible source windows. **16** name/address uses occur in `处女之死`; **10** uses in four other stories are parts of the ordinary adjective “软绵绵”. The actual source quotes, sample/message indices and UTF-8 digests are in the *private* R39 handoff. There is **no observed same-person-name collision arising from this exact string**. This does not certify independence of other character aliases, settings, rights or source-linked worlds. Occurrences may repeat because the same chat turns can appear in multiple candidate windows.

2. **All 82 original exact-copy rows retain valid actual HF `last_round` result IDs.** GitHub [Action 38499157328](https://github.com/sunxu/storyforge/actions/runs/38499157328) downloaded the private LFS R27 original input and the successful HF report from Job `6ace19935ccb47ba0f787af5`, independently rebuilt R30/R35/R36/R37 exclusions and recomputed four split hashes. It verified **21,807 supervised tokens** and **155,946 ms-swift input tokens** in the 82 unchanged rows, with the original model-run per-row label digest evidence. This is inherited source-row evidence only, not a new model run or full final batch-pack/loader validation.

3. **Four unsigned whole-story split options** now have verified *real supervised-token* budgets:

| Analysis-only split | Train rows | Train supervised tokens | Validation rows | Validation supervised tokens | Validation story sizes |
|---|---:|---:|---:|---:|---|
| R37 original | 65 | 16,823 | 17 | 4,984 | 16,1 |
| R38 Balanced A | **64** | **16,648** | **18** | **5,159** | **8,8,2** |
| R38 Diverse B | 66 | 16,597 | 16 | 5,210 | 8,5,2,1 |
| R39 Four-worlds | 63 | 16,368 | 19 | 5,439 | 8,8,2,1 |

   Preferred **conditional** split design is **Balanced A** because it reduces largest-story dominance to 44.4% (versus 94.1% original) while retaining 64 training rows. The four-world option improves largest-story share to 42.1%, but reduces training rows to 63 and includes a single-item validation story. All options remain **NOT_APPROVED**, with no provenance/IP/alias connected-component clearance. Sample-based validation can be extremely noisy with only 16–19 examples; publish per-story metrics rather than only pooled sample means.

4. **Scale risk is material:** A's Train includes only **16,648 labeled tokens**, far too little to assert broad 27B Qwen narrative quality improvement from this pilot alone. If ultimately approved, position the run as a constrained experimental signal rather than a reliable generalized adapter. R30's user approval covered the generic no-card *input design*, not unrestricted spend or release.

## Exact R39 assets

- Private R39 ZIP: `StoryForge_v02_R39_Decision_And_Alias_Evidence_20261014.zip`; SHA256 `0a4f2086dbaeb5fd3fc1f7f24d4930a27399e0d69ed64d7aacbf57fcb1b68c95`.
- Private R38 baseline: ZIP SHA256 `b4bbfcb5953d0d4337a25f57481ce55793731058966035be418bf8b046a61ddc`.
- Frozen R37 82 input SHA256: `f108c2b85ae096fd00e49e23e50d00b1cf0cf779682793ea6e3951e700b9e7c9`.
- Private package contains source-bound 26 excerpt witnesses, pending 82-row final decision queue, nine-story risk/inventory matrix, four unsigned split definitions and their data hashes, read-only verifier and SHA256SUMS, and original R38 archive. All ZIP members and source-row SHA checks passed on independent extraction. Intentional admission tampering was rejected. Marker: `R39_82_EXACT_SOURCE_FOUR_SPLITS_26_CONTEXTUAL_NAME_WITNESSES_PASS__NO_TRAINING_APPROVAL`. **No private witness text or Gold target text is uploaded in ordinary Git.**

## Actual remaining release decisions

- **82/82 final source-bound content, character age, player-autonomy, canon and rights signoffs are pending; 0 have signed admission.**
- Existing 25 source/IP-quarantined records remain isolated, with no claims of infringement.
- World-linked alias graph against original story records/v0.1 exposure not certified. The “绵绵” *single lexical false-positive* finding cannot satisfy this gate.
- Genuinely fresh, independent, sealed, pre-registered heldout remains **0**. R36's assistant-authored 20 auxiliary prompts are not official heldout.
- No final accepted Train/Validation/Test partition, no final assembled data loader/packing audit, and **no paid GPU launch authorization**.

**Recommendation for next task:** stop issuing more broad text-screening rounds. Use the R39 82-row decision ledger as the authoritative **unsigned** queue; independently sign high-risk age/source/prompt cases or exclude them, approve connected-world components, supply a fresh heldout, choose a full-story split, and only then build the immutable train/validation artifacts and last-mile loader preflight.