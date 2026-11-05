# R52 — Seven-world historical model exposure preflight

**Checkpoint:** Owner's 2026-10-20 Mac receipt `R52_FULL_SOURCE_21_21_REVIEW_RECEIPTS_RECONCILED__GRAPH_HOLD` established seven authenticated source stories, 20,577 original source-message hashes, 104 R51 target source pins, 21/21 full-original world pair decisions and 87 cited original messages. All routes were `NO_LINK_OBSERVED_IN_FULL_AVAILABLE_SOURCE__HOLD`, **not** proof that the worlds are truly independent. 46 target-quality preliminary candidates and 16 quality HOLDs; Train 0, Validation 0, GPU 0, R50 heldout unopened.

The **next independent gate** is exposure to historical trained/evaluated source material beyond direct inter-R52 story pairing. Prior Gold87 / v0.1 / R45 cohorts must not be treated as one interchangeable historical corpus.

## Available historical source comparators

- **v0.1 Train65/Validation15/Test20:** the immutable `data/compiled/v0.3/*.jsonl` bytes (SHA256 pinned by `v03_r52_world_exact_isolation.py`). Earlier exact UUID disjointness was confirmed against all 7 R52 stories; this step checks additional long text.
- **Gold87:** the frozen `evaluations/v0.2/gold-quality-87/gold_quality_accepted_87.jsonl` blob pinned by `v03_r51_gold195_readiness.py`. Gold87 is *not* automatically approved training exposure. Exact/long text and cross-story semantic comparison remain valuable despite distinct story UUIDs.
- **Private R45 Train49/Validation15:** frozen pre-R46 experimental source records; expect SHA256 `e7442993088617c4eaefd3a0c9efc7651932f7048f34586046bf6d5b5981a742` (Train49) and `5ebbb3c6986a5ac4d294175bab1980ee61df08536f9b8438c8a67010630f1963` (Val15). The exact two private JSONL files must be explicitly supplied if available. Omitting either file alone triggers HOLD; omitting both still allows v0.1/Gold87 screening but leaves **R45 coverage explicitly incomplete**.

## Mac execution (read-only input)

```bash
cd ~/workspace/storyforge
git switch audit/r49-r50-source-intake-20261015
git pull --ff-only

d="$HOME/.local/share/storyforge"
install -d -m 700 "$d/r52/history_exposure"

python3 scripts/v03_r52_historical_exposure_triage.py \
  --repo . \
  --source-zip "$d/r52/remaining18/R52_REMAINING_18_FULL_ORIGINAL_WORLD_REVIEW_PRIVATE.zip" \
  --graph21-receipt "$d/r52/graph21/R52_ALL_21_WORLD_GRAPH_SAFE_AGGREGATE.json" \
  --out-dir "$d/r52/history_exposure"
```

If the exact frozen private R45 files are already present on the owner's Mac, include both options in the same run:

```text
--r45-train "/actual/private/path/R45_TRAIN_FROZEN_CANDIDATE_49_NOT_APPROVED.jsonl"
--r45-validation "/actual/private/path/R45_VALIDATION_FROZEN_CANDIDATE_15_NOT_APPROVED.jsonl"
```

These are path **examples**, not claims the private R45 files exist in a particular directory. Do not run the first command and then the optional second version using the same output directory: output files are create-only and will reject overwrites.

Expected owner-local completion marker:

`R52_SEVEN_WORLD_HISTORICAL_EXPOSURE_SCREEN_COMPLETED__SEMANTIC_HOLD`.

Private outputs:
- `R52_PRIVATE_HISTORICAL_EXPOSURE_WITNESSES.jsonl`: candidate exact long-message / sampled 120-codepoint reuse witnesses, with source rank, original message array index and SHA256 and historical record/message ordinals; private evidence only, never commit to public Git.
- `R52_HISTORICAL_EXPOSURE_SAFE_AGGREGATE.json`: fixed provenance hashes, counts of exact story-ID collisions, long-message / sampled-fragment leads, explicit R45 coverage flag and no-admission statuses.

**Critical method limits:** text matching normalizes NFKC, casefold and whitespace and samples 120-codepoint windows in strides of 40; it is *not exhaustive all-offset search*, not entity resolution, not paraphrase detection, and not a final semantic-world clearance. Any common service/policy text may be a benign shared template; flag it for private contextual review rather than interpreting it as shared fictional canon. When no match is found, hidden aliases, rephrasing, independent-character equality and trained story-state exposures remain unverified.

Do not unseal R50 independent tests. Existing historical model exposures and complete author world links must be reviewed by the owner before component separation; separately sign final per-case content/safety for all 46 preliminary quality candidates, then test exact no-card prompt/input and ms-swift target label masks before proposing a Train/Val split.

**No training admission has occurred.**


## 2026-10-20 follow-up — verified R45 original ZIP without persistent extraction

Owner's first local exposure-screen report:
`R52_SEVEN_WORLD_HISTORICAL_EXPOSURE_SCREEN_COMPLETED__SEMANTIC_HOLD`.
**7** R52 source story exports (20,577 source messages) were screened against 87 Gold87 examples and the pinned v0.1 Train65 / Val15 / Test20; there were **zero exact story-ID collisions** and **zero sampled long-text candidate witnesses** under the stated algorithm. **R45 was explicitly NOT included**, so this report is not final historical exposure clearance, and no story components were signed.

The updated `scripts/v03_r52_historical_exposure_triage.py` can now read the **owner-held original frozen R45 private ZIP** directly using `--r45-original-zip`, with byte-level SHA256 and count pin checks for the original Train49/Validation15 JSONL members, in an ephemeral 0700 temporary directory. Duplicate named members, changed SHAs/counts, symlinks and inappropriate modes fail closed. No private R45 source bytes are persisted in Git or retained by the script after successful execution. Keep the original ZIP itself offline/private.

Example for owner-local run when the ORIGINAL R45 ZIP exists:

```bash
cd ~/workspace/storyforge
git switch audit/r49-r50-source-intake-20261015
git pull --ff-only

d="$HOME/.local/share/storyforge"
R45_ORIGINAL_ZIP="/absolute/private/path/to/owner-preserved-r45-original.zip"
install -d -m 700 "$d/r52/history_exposure_with_r45"

python3 scripts/v03_r52_historical_exposure_triage.py \
  --repo . \
  --source-zip "$d/r52/remaining18/R52_REMAINING_18_FULL_ORIGINAL_WORLD_REVIEW_PRIVATE.zip" \
  --graph21-receipt "$d/r52/graph21/R52_ALL_21_WORLD_GRAPH_SAFE_AGGREGATE.json" \
  --r45-original-zip "$R45_ORIGINAL_ZIP" \
  --out-dir "$d/r52/history_exposure_with_r45"
```

The example R45 path is illustrative, not an assertion about where the private ZIP exists. The separate output directory avoids overwriting the first historical screen. If R45 frozen **loose** files are already present, the earlier two-argument `--r45-train` / `--r45-validation` route remains available; the ZIP option is **mutually exclusive** with those loose-file options.

R45 historical candidates may involve some of the same numbered original stories as R52. If direct source story UUID or identical long dialogue hits are observed, treat them as **exposure evidence requiring per-model/per-split review**, not as harmless name coincidences or automatic permanent exclusion from all future training. It would particularly preclude unqualified claims of an independent unseen validation world for a model previously exposed to that story.

**No GPU, no Train/Val assignment, no R50 sealed test access, no seven-world semantic-independence certificate.** Synthetic SHA/ZIP/tamper CI: https://github.com/sunxu/storyforge/actions/runs/39410839236.


## 2026-10-20 — Owner R45 verified archive screen reveals historical source reuse

Owner-local run with private R45 original ZIP SHA256 `da4b7718f1c1cbd0429553b684eeaf70f207fd2e41aae4e8fe0a52a11b647b9e`:
`R52_SEVEN_WORLD_HISTORICAL_EXPOSURE_SCREEN_COMPLETED__SEMANTIC_HOLD`.

- Authenticated R45 Train49 / Validation15 source hashes `e7442993088617c4eaefd3a0c9efc7651932f7048f34586046bf6d5b5981a742` / `5ebbb3c6986a5ac4d294175bab1980ee61df08536f9b8438c8a67010630f1963`.
- **29 Train rows + 13 Validation rows** have source-story UUIDs exactly matching one of the seven R52 story UUIDs. These are **row counts, not numbers of distinct worlds**, and Train vs Validation have different implications.
- **537 text-overlap witnesses**, **273** normalized exact long-message records and **264** sampled 120-codepoint fragments. Witnesses are *not* distinct target counts or independent reviewed contamination instances. Duplicates or multiple hit routes may arise.
- Gold87 and v0.1 Train/Validation/Test remain source-hash verified, with zero additional exact-ID and sampled long-text matches under this screen.
- All 46 preliminary quality candidates remain `PENDING_NOT_APPROVED`; no new Train/Val split, no signed world components, no GPU, no R50 unsealing.

**Important gate change:** Seven R52 worlds can no longer be described as unexposed independent worlds without model/split-specific R45 source lineage review. Next: rank-deduplicated per-world historical collisions, direct target-SHA equality, 46-case risk partition and evidence witness provenance verification. Do not count 537 as 537 unique contaminated messages or assume an R45 validation record was used to optimize R46 weights without a training/run manifest.
