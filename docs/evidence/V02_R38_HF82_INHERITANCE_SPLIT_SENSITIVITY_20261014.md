# StoryForge v0.2 — R38 real HF subset evidence and validation diversity finding

**2026-10-14. User said “继续” after R37. No training or dataset-release authorization granted. Formal admission remains `PENDING_NOT_APPROVED`.**

## A. Engineering evidence inherited with no paid rerun

The current conditional review shortlist is **82 exact original JSONL rows** from the private R27 dataset of 117. Its SHA256 is `f108c2b85ae096fd00e49e23e50d00b1cf0cf779682793ea6e3951e700b9e7c9`. Existing 65 Train / 17 Validation proposals remain byte-exact and **unsigned**.

New independent [GitHub Actions run 38428606867](https://github.com/sunxu/storyforge/actions/runs/38428606867) **SUCCESS**:
- Downloaded full original R27 input archive and the actual R27 HF report from private Git LFS.
- Independently verified the original 117-result HF JSON from Job `6ace19935ccb47ba0f787af5`: SHA256 `e23f166226142e28a04f42a3d481776b6ac84d9b30f92e30a55de838e5d2b213`.
- Reconstructed the unchanged 82 lines by exactly replaying R30's 25 provenance quarantine, R35's 3 missing-visible-premise holds, R36's 4 preliminary window holds and R37's 3 preliminary window holds.
- Checked each of the 82 samples for unchanged original target SHA, only-final-Assistant supervision flag, report sample ID, story UUID, per-row `ACTUAL_LAST_ROUND_INTERNAL_PASS` and valid label-evidence digest.
- New **R38 original-HF-evidence subset aggregates:** **82/82** IDs covered; **155,946 ms-swift tokens**, **21,807 supervised tokens**, maximum **3,694 tokens**. No real HF Job was rerun.
- Independently computed original conditional split hashes and checked zero identical **normalized 16-character contiguous dialogue substrings** between Train/Validation, excluding the identical synthetic System instruction.

Result marker: `R38_INHERITED_PER_ROW_REAL_HF_MASK_EVIDENCE_PASS_ONLY`. This establishes per-row engineering evidence inheritance **only for byte-identical rows under the original HF setup**. Batch packing, final revised splitting, full compiled loader and other trainer behaviors were not replayed. The original R27 API report contains label digests, not per-token arrays.

## B. Newly identified validation concentration problem

The R37 proposed Validation set has **17 samples but 16 of them belong to one story UUID**, with the last 1 from a second. The largest world contributes **94.1%** of its sample rows and the inverse-Simpson effective count is about **1.125** independent contributing story groups. This is a weak evaluation signal for cross-story narrative quality, even though Train and Validation UUIDs are disjoint.

Two **alternative unapproved** entire-story reallocations were computed without modifying any examples:

| Proposal | Train | Validation | Validation groups | Largest group share |
|---|---:|---:|---|---:|
| R37 unchanged | 65 | 17 | 16, 1 | **94.1%** |
| R38 Balanced A | 64 | 18 | 8, 8, 2 | **44.4%** |
| R38 Diverse B | 66 | 16 | 8, 5, 2, 1 | **50.0%** |

All three have zero observed exact normalized 16-char cross-split dialogue matches in the current R27-visible messages. **No proposal has been accepted**. This string-overlap result is not a world/alias/IP or semantic overlap certificate. The split proposal should be selected only after story linkage and source rights are resolved.

## C. Human decisions still required

- **82/82** candidates have evidence-linked but **PENDING** final content/age, player autonomy, source rights, world components and split signoffs. R31–R37 review is evidence and suggestions; it is not a signed final adjudication.
- **25** other candidates stay provisionally quarantined on third-party origin/IP questions. The three older and seven newer window-HOLD recommendations are excluded *from the 82 shortlist* but do not cancel historical Gold quality acceptance.
- Nine distinct story UUIDs among 82 are not a proven connected-component isolation graph.
- Genuine new independent sealed heldout stories/prompts **still 0**. R36's 20 synthetic smoke tests are not misrepresented as official heldout.
- Final training data release, paid GPU authorization and optimizer launch **remain blocked**.

## Private package and reproduction

Private handoff: `StoryForge_v02_R38_Subset_Inheritance_And_Split_20261014.zip`, SHA256 `b4bbfcb5953d0d4337a25f57481ce55793731058966035be418bf8b046a61ddc`. Includes immutable R37 baseline, 82-row ID/hash-only trace, nine story groups, pending 82-row approval packet, two unapproved split alternatives, GitHub remote HF proof summary, reproducible read-only inference script and offline `verify_r38.py`. No new standalone raw chat JSONL beyond the unchanged nested private R37 ZIP.

Offline result: `R38_82_INHERITED_HF_REAL_REPORT_AND_SPLIT_SCENARIOS_EVIDENCE_PASS_ONLY__NO_GPU_RELEASE`, and a tampered review sheet was rejected with exit 2. Confidential zip is not committed to ordinary Git source; only abstract audit documentation and the CI action are checked in.

**Engineering finding:** avoid another paid CPU Token/Mask run for the same unchanged 82 rows *solely to confirm original per-row labels*. Still do a final data-loader/batch-preflight before any authorized GPU training, especially if split, packing or input schema changes. Do not infer release approval from hashes.
