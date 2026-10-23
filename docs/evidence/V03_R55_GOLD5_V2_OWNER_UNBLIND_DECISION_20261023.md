# StoryForge R55 Gold5 v2 — Owner unblind and current candidate decision

Date: 2026-10-23 (Asia/Singapore). Source evidence: Owner-pasted count-only local `R55_GOLD5_V2_OWNER_UNBLIND_SAFE_AGGREGATE.json`, schema `storyforge-r55-gold5-v2-owner-unblind-aggregate-v1`, status `R55_GOLD5_V2_OWNER_ONLY_UNBLIND_AGGREGATED__DEVELOPMENT_ONLY__NO_R50`. This record does not claim that the assistant personally downloaded or rehashed nine private scored CSVs, inspected source content, or checked the private mapping bytes; the Owner's local script reported the latter validations. No private question, story, reviewer text or per-case identity mapping is included here.

## 0. Release decision

**`R55_GOLD5_V2_R54_CHECKPOINT16_DEV_GATE_FAIL__NO_GO_FOR_R50_NOW__R46_COMPARATOR_RETAINED__CASE_EVENT_ADJUDICATION_PENDING__NO_MODEL_PROMOTION`**

This is a decision not to spend the presently reserved R50 evaluation on unchanged R54 v0.3-A checkpoint-16, nor to promote its quality, *not* proof of its unseen-world performance. The previous R55 direct pairwise (12 R54 wins versus 8 R46 wins, using old frozen alternative reviews) did not have a six-axis improvement; this newer independently blinded v2 comparison is 10:10 while v0.3-A is lower in every dimension across Pair/Four/Five. Do not pool the scores, or treat multiple rounds or 3 Reviewers as independent test cases. R50 remains unopened and formally unadmitted.

## 1. Receipt and scope

- 20 reused exposed R47/R48/R55 development prompts from 2 story worlds; three reviewers; Pair ratings 720, Four 1440, Five 1800 = 3960. Four model responses from Base, v0.1, v0.2/R46 and v0.3-A/R54; the fifth answer in Five is an original same-prompt historical Gold reference, not another model or gold-standard correctness.
- Frozen v2 preparation SHA256 `6476da25e7d6b043a7bec3d413bfc75885c8571c188f318e3a4eb523888bdaa4`; Owner-verified coordinator key SHA256 `fc328688fac957c849d822d82db841479105afb0c885b48b381b1a270f9f3334` (key not shared).
- Owner-reported freeze-receipt hashes: Pair `ff1c81c39ff9983c64cc8cc43c68028e8e306a6bb28fd351eaabdd05f9af9747`; Four `664f4685c58c37fc817322aae523059e95da39df38e691384b28aac5394be506`; Five `2eb71a88f714226c10e45349067a1848650c20ea8a6211da7f45200f2c145bc0`.
- Source declares adjudication_complete=false, status_constraints.reviewer_independence_human_attested_not_technically_proven=false (no technical certification). No new inference, HF GPU or R50 reads.

## 2. Independent Pair: v0.3-A versus v0.2, 20 cases

| Metric | v0.2 R46 | v0.3-A R54 |
|---|---:|---:|
| Majority cases | 10 | 10 |
| Reviewer preferences out of 60 | 30 | 30 |
| Overall six-axis mean (1–5) | **3.363889** | 3.216667 |
| Story continuity | **3.566667** | 3.433333 |
| Character consistency | **3.766667** | 3.566667 |
| Instruction adherence | **2.833333** | 2.700000 |
| Literary expression | **3.650000** | 3.550000 |
| Interactive progression | **3.483333** | 3.233333 |
| Player agency | **2.883333** | 2.816667 |
| Provisional agency flagged distinct cases (any reviewer) | 5/20 | 5/20 |
| Provisional banned/hard-fact flagged distinct cases | 10/20 | 10/20 |

Direct Pair v0.3 win fraction 10/(10+10)=**0.5** (not >0.5), difference in six mean v0.3 - v0.2 = **-0.147222**. The declared proposed R56 gate of >0.5 direct win AND six-axis mean improvement and no literary/interaction regression is not met. No need to wait for problem adjudication to make this *current candidate non-advancement* decision. The thresholds remain a proposed Owner-unapproved formal evaluation contract: this is a conservative **development gate** decision, not a completed formal R50 release assessment.

## 3. Four-model ranking, same 20 old cases independently rated

| Arm | Case-majority wins | Reviewer preferences | Overall six-axis mean |
|---|---:|---:|---:|
| Base | 5 | 14 | 3.330556 |
| v0.1 | 5 | 15 | 3.186111 |
| **v0.2 R46** | **7** | **20** | **3.486111** |
| v0.3-A R54 | 3 | 11 | 3.269444 |

Four: v0.2 exceeds v0.3 by +0.216667 overall, and in all six individual axes. Its preliminary agency flagged case count is 6, versus v0.3=7; banned/hard-fact counts v0.2=10, v0.3=7 (unadjudicated, not confirmed failures).

## 4. Five-way original-Gold reference comparison

| Arm | Case-majority wins | Reviewer preference votes | Overall six-axis mean |
|---|---:|---:|---:|
| Base | 2 | 5 | 3.291667 |
| v0.1 | 4 | 14 | 3.275000 |
| **v0.2 R46** | **6** | **18** | **3.461111** |
| v0.3-A R54 | 2 | 9 | 3.197222 |
| Original Gold (historical reference) | 4 | 14 | **3.500000** |
| No majority | 2 | — | — |

Five: original Gold has the highest mean by +0.038889 vs v0.2, but v0.2 is the strongest *model* in mean/preference/case majorities. Gold literary 4.083333 versus v0.2 3.783333; Gold player agency 2.516667 versus v0.2 2.933333. Thus Gold is useful as literary reference but not an infallible instruction/agency target. Five preliminary flagged cases agency: Gold 11/20, v0.2 6/20, v0.3 7/20; forbidden/hard-fact: Gold 6/20, v0.2 10/20, v0.3 7/20. **All are unadjudicated screening flags**. v0.3 mean is 0.263889 below v0.2 in Five, also lower on all six axes.

## 5. Action, bounded interpretation and next evidence

1. **Freeze no changes** to the existing nine Reviewer CSV files, SHA, prompts, model replies and R54 checkpoint-16. Treat R55 v2 as complete for developer statistics, no repeated relabeling or new model jobs.
2. Independently adjudicate flagged *concrete events* based on original prompt/history/rules, exact candidate reply, and quote-grounded Reviewer reasoning. Preserve reviewer blindness to source/arm when possible. Cases may have multiple categories; collapse duplicate mentions by (case, response, event), including across Pair/Four/Five rounds. For each candidate event record `CONFIRMED`/`REJECTED`/`HOLD_INSUFFICIENT_EVIDENCE`, category, quoted evidence, context rule, adjudicator identity, and source SHA. Only count **distinct confirmed case+arm events** in final severe error rates; reviewer-case arm marks are NOT product error rates. Distinct case-level serious agency count threshold 5% would permit at most 1/20, if ever applied on 20 comparable cases (but this exposed dev set is inadequate for generalization). The lower hard-flag case count of v0.3 alone does not outweigh quality regressions.
3. Use the private case-level unblind report to rank v0.3's recurring character-consistency and interactive-progression weaknesses relative to v0.2 and source Gold; perform targeted data and prompt analysis on **already exposed** examples only, not R50.
4. Keep v0.2 as the comparison baseline; do not treat its standing in old 20 developer cases as formal certification. A new v0.3 revision would need frozen training authorization, allowed data and an independent fresh multiworld test gate. R50 remains pre-seal and not authorized as a debugging set. Original Gold for R50's independently authored new prompts is still unavailable unless a literal prompt-matched original reply is authenticated.

**Status:** `R55_GOLD5_V2_DEV20_UNBLIND_REPORTED_PASS__R54_NO_GO_R50_NOW__HARD_EVENT_ADJUDICATION_PENDING__NO_MODEL_PROMOTION`.
