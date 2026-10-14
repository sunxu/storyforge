# StoryForge v0.2 — R47 Three-Reviewer Blind Scores: Frozen Git Audit (Pre-Unblind)

**Date:** 2026-10-14. **Current gate:** `THREE_COMPLETED_CSV_GIT_FROZEN_SHA256_CI_PASS_PRISTINE_ORIGINAL_COMPARE_PENDING`.

Three reviewer-completed 20-line sheets have been committed by the owner on main at immutable commit `04fbf45e73ec824c25d2692c8e6a6ebf4ca14a7d` (message: `eval(r47): archive three independent blind reviews`). Complete 1,080 integer rating cells, all required preference/evidence/severe markers, stable case IDs and 100% identical input & A/B/C response columns **among these three submitted sheets** were verified. Each of the 60 scored records has at least one quote matching the submitted context or response. This is *not* an exhaustive semantic audit of every quotation.

## Frozen CSV bytes

| Completed rating sheet | Git blob SHA-1 | SHA256 from CI |
|---|---|---|
| `R47_Reviewer_01_completed.csv` | `9f7adee4bb084513dd98a39c5cf91215aa7a32ed` | `ed1151970ad272efe76962bbec4662e18d903f3567bbf762a6b82c860c657ef5` |
| `R47_Reviewer_02_completed.csv` | `1af161b578966d835a3fede409e2146814252303` | `67d9a9b81e68defd9ad5f71075d3c4c2f80d85b98a99941a2c7922ba23d34783` |
| `R47_Reviewer_03_completed.csv` | `6d70353e035f3d335276c1535c8801b848a942c1` | `69e067d6f05d4429eb6c5fe8f7dc278d57098b0744552637e9916b2d4423ef17` |

The specialized GitHub Actions [R47 blind regression CPU guard run #38565580015](https://github.com/sunxu/storyforge/actions/runs/38565580015) passed the original 20-case manifest check, 10 existing pipeline tests, and actual committed R47 three-review freeze audit with no key access.

## Anonymous preference, before model mapping

- Reviewer 01: A=9, B=6, C=5; Reviewer 02: A=12, B=6, C=2; Reviewer 03: A=12, B=5, C=3.
- Pooled 60 individual votes: A=33, B=17, C=10; TIE=0.
- Sample-level majority winner across 20 cases: **A=11**, **B=6**, **C=3**. Agreement: 16 unanimous 3/3 cases, 4 split 2/1 cases, no three-way splits.
- Mean six-dimension score pooled across three independent reviewers and 20 cases (360 scores per letter): A **3.3333**, B **2.9361**, C **2.8833**.
- Serious player-agency flags across all 60 reviewer-case records: A=1, B=6, C=19, no severe flag=34. Two preference/severe marker conflicts need evidence-level adjudication: Reviewer 03 `eval-016-193774e13ceb` and Reviewer 01 `eval-019-22cc0fa9229a`.
- The three sheets contain no identical complete rating-rationale fields for the same case between reviewers, but **reviewer independence and no previous exposure cannot be established solely from CSV metadata**.
- The study uses **previously exposed v0.1 retrospective Test 20**, not independent new Held-out, and cannot authorize model promotion.

## Required last verification before opening private key

The immutable Git CSVs match one another for prompt and response fields, but that alone cannot prove all three were left unchanged relative to the original **private, blank** R47 reviewer exports in the owner's collector directory. Compare those originals locally before unblinding:

```bash
cd ~/workspace/storyforge
git pull --ff-only origin main
ROOT="$HOME/.local/share/storyforge/r47/r47-20261014T091647Z-637890"
mkdir -p "$ROOT/coordinator/preunblind"
python3 scripts/v02_r47_review_freeze.py \
  --reviews-dir evaluations/v0.2/r47/reviews/round1 \
  --manifest evaluations/v0.1/test/manifest.json \
  --pristine-dir "$ROOT/reviewers" \
  --output "$ROOT/coordinator/preunblind/R47_SCORING_FREEZE_PRIVATE.json"
```

Required marker: `R47_THREE_INDEPENDENT_SCORING_FILES_FROZEN_PRE_UNBLIND`. This strictly matches frozen Git blobs, every original story/context/input/reply column against each original unscored reviewer CSV, confirms all original scoring columns were blank, verifies all 60 scored cases and quoted evidence, and records SHA256 of all scored reviewer files.

Then run the existing scoring completeness test **without** the key:

```bash
python3 scripts/v02_r47_review_aggregate.py \
  --manifest evaluations/v0.1/test/manifest.json \
  --reviews evaluations/v0.2/r47/reviews/round1/R47_Reviewer_01_completed.csv \
    evaluations/v0.2/r47/reviews/round1/R47_Reviewer_02_completed.csv \
    evaluations/v0.2/r47/reviews/round1/R47_Reviewer_03_completed.csv
```

Expected marker `R47_THREE_REVIEWERS_20_CASES_COMPLETE_KEY_NOT_READ`. Only after both passes should the coordinator privately run that same aggregate command with `--key "$ROOT/coordinator/private/R47_PRIVATE_ANSWER_KEY.json" --output "$ROOT/coordinator/preunblind/R47_PRIVATE_UNBLIND_DIAGNOSTIC.json"`. **Never add the private answer key or original story text to Git anew.** The full CSVs already committed by the owner contain private narrative contexts and replies; Git history retains those bytes. Confirm that repository permissions remain private.

This document does not assert that the original private CSV comparison has already passed, nor that the private key was read. `unblind_approved=false` until local pristine comparison succeeds.
