# StoryForge v0.2 — R47.1 three-arm blind regression: owner-reported full collection PASS

**Date:** 2026-10-14  
**Status:** `R47_THREE_ARM_20_60_BLIND_INTEGRITY_PASS_NO_PROMOTION` — **OWNER-REPORTED MAC VERIFICATION**, not independently re-hashed by this GitHub documentation commit.

## Scope and known evidence

- Previous full R47 HF Job `6acf3b8fc66288145223b41e` failed after saving Base 20/20. Original Base result SHA256, verified by owner via CPU-only recovery check: `becd890268edb1002c3f7195a1906f73045a86643fdac45eaf7090ee82d4dcfe`.
- Resumed Job `6acf48935ccb47ba0f79853d`, run `r47-20261014T091647Z-637890`, was reported completed; generated 20 v0.2 responses in last infer step, together with v0.1 results and reused Base.
- Owner ran Git-native `scripts/v02_r47_collect_git.sh` from Mac and supplied the terminal marker `R47_THREE_ARM_20_60_BLIND_INTEGRITY_PASS_NO_PROMOTION`. That program performs 20/20/20 original-prompt-to-response matching, raw-result and blind package SHA comparisons with HF report, Base recovery SHA, model-identity and v0.1/v0.2 adapter IDs, 20-way private A/B/C mapping and reviewer CSV crosschecks. **Source files from that local private verification were not provided to this review session**, so we record the CLI's PASS statement rather than claiming an independent second rehash.
- Historical v0.1 **20 exposed Test prompts**, 60 new model responses, 3 blank reviewer CSVs. **Zero scored reviewer files reported received at this point.**
- Old Test has been used before in v0.1 comparisons and historical reviewer output, so this is a *retrospective regression comparison*, never new independent Held-out.
- The historical prompts include rich embedded character and world cards; R46 v0.2 training used a generic no-card prompt. All inference arms receive identical old inputs, but do not interpret this comparison as covering all v0.2 deployment modes.

## Reviewer delivery — NO LFS / no ZIP / no GPU

The local Git-native collector stores its verified results outside Git:

```text
~/.local/share/storyforge/r47/r47-20261014T091647Z-637890/reviewers/
  R47_Reviewer_01.csv
  R47_Reviewer_02.csv
  R47_Reviewer_03.csv
  R47_BLIND_THREE_WAY_20.jsonl

~/.local/share/storyforge/r47/r47-20261014T091647Z-637890/coordinator/
  R47_PRIVATE_RUN_REPORT.json
  base-results.jsonl
  v01-results.jsonl
  v02-results.jsonl
  private/R47_PRIVATE_ANSWER_KEY.json
  private/R47_AUDIT_SUMMARY.json
  R47_LOCAL_INTEGRITY_PASS.json
```

**Important:** Assign **one CSV per independent reviewer**. Do not share `coordinator/`, the private key, model-named raw results, previous v0.1 reviewer scores, or any information associating A/B/C with models. Do not push raw story text, model replies, reviewer sheets, the key, or this locally collected archive to ordinary Git.

Reviewers ideally were not involved with the old v0.1 Test and have not seen the earlier A/B adjudications. All reviewers use the same frozen rules below, assess separately, and must not compare scores or discuss guesses until all 3 are locked.

## Rating instructions

For **each of all 20 cases**, read the Story/System context, previous messages, current User input and 3 anonymous candidate replies. Assess the **same six dimensions for A/B/C on 1–5 scale**: 
1. 剧情连续性 — respects established chronology, relationships and event state.
2. 角色一致性 — behavior/dialogue consistent with character and setting.
3. 指令遵循 — obeys explicit standing and current User boundaries/constraints.
4. 文学表现力 — fluency, vivid specificity, style fit, nonformulaic dialogue.
5. 互动推进 — meaningful narrative initiative without forcing player action.
6. 玩家自主权 — does **not** author the player's private thoughts, independent choices, speech or forced decisions. A seriously agency-violating model cannot win solely by writing beautifully.

For each case, complete **all mandatory scoring cells**: `整体最佳(A/B/C/TIE)`, all 18 score cells (6×3), `评分理由与逐字证据`, `严重问题与对应回复`, and `玩家自主权严重侵犯(A/B/C/无)`. Use `TIE` only when no defensible single best reply; never leave blanks because models are close. If no severe issues, explicitly put `无`. Cite a word-for-word span from the reply and the relevant User/context line whenever possible; don't invent unsupported world details or edit source text. A serious breach should be noted even in a preferred reply.

Make no edits to `样本编号`, prompt, contexts or A/B/C response content; do not reorder or insert rows. Fill scores and explanations only.

## Collect and verify completed blind reviews before opening private key

Place the **three completed files** under a new private path, such as `~/.local/share/storyforge/r47/ratings-r01/`. Avoid replacing source blank sheets and preserve the original reviewer files.

Before unblinding, validate complete individual scoring with the existing script:

```bash
cd ~/workspace/storyforge
python3 scripts/v02_r47_review_aggregate.py \
  --manifest evaluations/v0.1/test/manifest.json \
  --reviews \
    "$HOME/.local/share/storyforge/r47/ratings-r01/R47_Reviewer_01.csv" \
    "$HOME/.local/share/storyforge/r47/ratings-r01/R47_Reviewer_02.csv" \
    "$HOME/.local/share/storyforge/r47/ratings-r01/R47_Reviewer_03.csv"
```

Expected: `R47_THREE_REVIEWERS_20_CASES_COMPLETE_KEY_NOT_READ`.

Preserve read-only copies and SHA256s of all three completed original review sheets **before** decrypting/opening `R47_PRIVATE_ANSWER_KEY.json`. Then only the review coordinator executes:

```bash
R47_ROOT="$HOME/.local/share/storyforge/r47/r47-20261014T091647Z-637890"
REV="$HOME/.local/share/storyforge/r47/ratings-r01"
python3 scripts/v02_r47_review_aggregate.py \
  --manifest evaluations/v0.1/test/manifest.json \
  --reviews "$REV/R47_Reviewer_01.csv" "$REV/R47_Reviewer_02.csv" "$REV/R47_Reviewer_03.csv" \
  --key "$R47_ROOT/coordinator/private/R47_PRIVATE_ANSWER_KEY.json" \
  --output "$REV/R47_PRIVATE_UNBLIND_DIAGNOSTIC.json"
```

Expected: `R47_RETROSPECTIVE_AGGREGATE_PASS_NOT_MODEL_PROMOTED`. Output contains per-arm raw preference votes, majority choices and six-dimension means; do not reduce contradictory reviews to a false consensus. Reviewers' evidence and serious-issue severity still need qualitative analysis. A formal model promotion remains blocked pending **new independently authored and sealed 40–60 Held-out cases across ≥4 unused stories/worlds**.

## Do not rerun GPU

**R47 inference is complete according to the owner's provided logs and local PASS result.** No additional paid Job should be launched to begin the independent blind review.
