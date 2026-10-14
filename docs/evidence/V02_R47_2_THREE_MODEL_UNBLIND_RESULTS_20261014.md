# StoryForge v0.2 — R47 Three-Arm Regression: Unblinded Results

**Date:** 2026-10-14  
**Disposition:** `R47_RETROSPECTIVE_REVIEW_ONLY_NOT_PROMOTED`. v0.2 is the **leader on the previously exposed v0.1 20-prompt regression**, **not approved for model-quality promotion**.

## Evidence and scope

- Owner uploaded `R47_PRIVATE_UNBLIND_DIAGNOSTIC.json`, exact SHA256 `086861daa047cf2426344d1b9da47574e7363592968579bc7eb724d19896710c`; report source did not include the private letter↔model key.
- Three reviewer sheets were frozen in Git commit `04fbf45e73ec824c25d2692c8e6a6ebf4ca14a7d`; [pre-unblind scoring evidence](V02_R47_PREUNBLIND_SCORING_FREEZE_20261014.md) and the [GitHub no-key CI PASS](https://github.com/sunxu/storyforge/actions/runs/38565580015).
- Old 20 test prompts from **previously exposed v0.1** evaluation; not fresh Held-out. Three independent *ratings*, not 60 independent story items. The previous blind evaluation exposed historical model outputs and adjudications.
- The private answer key was **not opened in this audit turn**; results are as reported by the uploaded private unblind diagnostic. Per-case vote multiplicities, anonymous sample winners, total votes and group averages were checked for internal consistency against the previously frozen sheets where independently possible. Original private blank reviewer CSVs were not re-uploaded; pristine comparison is not independently certified by this report.

## Main result

| Model | Majority winner among 20 samples | Raw individual preference votes (60 total) | Overall mean across six scoring dimensions |
|---|---:|---:|---:|
| v0.2 / R46 checkpoint-7 | **11 (55%)** | **31 (51.7%)** | **3.242/5** |
| Base Qwen3.8-27B | 5 (25%) | 16 (26.7%) | 3.003/5 |
| v0.1 checkpoint-9 | 4 (20%) | 13 (21.7%) | 2.908/5 |

**Not a head-to-head win rate:** a three-choice “best of Base/v0.1/v0.2” is not the same as separate pairwise comparisons. There were 16 unanimous majority decisions and 4 cases decided 2:1, none all-different. There is also no variance-based confidence interval in the uploaded report.

### Six dimensions (mean of 3 reviewers × 20 items, full 5-point scale)

| Dimension | Base | v0.1 | v0.2 |
|---|---:|---:|---:|
| 剧情连续性 | 3.100 | 3.100 | **3.417** |
| 角色一致性 | 3.267 | 3.217 | **3.483** |
| 指令遵循 | 2.650 | 2.733 | **3.000** |
| 文学表现力 | **3.467** | 2.900 | 3.400 |
| 互动推进 | 3.183 | 3.217 | **3.450** |
| 玩家自主权 | 2.350 | 2.283 | **2.700** |

v0.2 beats both Base and v0.1 on five of six measured dimensions. **Base slightly leads literary quality**. Overall v0.2 +0.239 over Base and +0.333 over v0.1 points. This is descriptive on the fixed old sample set; not proof of generalization.

## Disagreement and failure analysis

**Four 2:1 samples:**

- `eval-010-95fc6ec25be5`: v0.2 2, Base 1. The reviews describe an ungrounded reversal of the coal-brazier directive and repetitive/presumptive “你写他…” writing in other answers. See source for which failing letter maps to each losing arm; don't infer unproven identities.
- `eval-012-bf902fa5b002`: v0.2 2, v0.1 1. The winner keeps character skepticism after the player's “responsibility” pledge. Other answers introduced ungrounded events or distorted birth-time character facts.
- `eval-014-7add48022d9a`: v0.1 2, Base 1. **v0.2 = anonymous B by elimination** (v0.1=C, Base=A). v0.2 B includes the explicitly prohibited phrase `你只能是我的。`, while the original System context contains that hard banned string. All reviewers flag this as an instruction-following violation. **Hard-constraint regression remains.**
- `eval-019-22cc0fa9229a`: Base 2, v0.1 1. **v0.2 = anonymous B by elimination** (Base=A, v0.1=C). v0.2 B drives user actions without authorization, including `你端起那盅血燕粥`, and is criticized for identity confusion. **Player-agency failure remains.**

**Relative preference vs severe player-agency flags:**

- `eval-016-193774e13ceb` unanimous Base/anonymous B. Reviewer 03 preferred B **and** recorded severe agency violation of B (`你再次张口，就着他的手将粥咽下`). This is not necessarily a scoring error: all three candidate responses were described as worse than ideal, and B was chosen as *least bad*.
- `eval-019-22cc0fa9229a` Reviewer 01 preferred v0.1/anonymous C **and** flagged C for severe agency violation (`你走过去，伸手去够那盏烛台`). Other two reviewers preferred Base A. Again, relative best can still be a failure; these records should retain their original votes and risk flags, not be silently “corrected”.

These are traceable issues in the frozen anonymous reviewer sheets, **not invented post-hoc criticism**. No reviewer scores or original responses were modified. Do **not** treat all A/B/C severe-marker counts as model-specific: letter mappings differ per sample, and the uploaded diagnostic does not contain the complete mapping or per-model severe-flag aggregations.

## Decision

1. **R47 retrospective regression preference: v0.2 leads**. Keep existing R46 checkpoint-7 and its private HF Bucket evidence; no GPU retraining is needed to establish these descriptive results.
2. **Quality promotion: NOT APPROVED**. The sample set is old/exposed and contains only two original story worlds; it does not test enough independent world components. Model training vs evaluation contracts also differ: the R46 fine-tune used generic no-card System prompts whereas original v0.1 Test includes rich character and story cards.
3. **Hard failure gates remain OPEN**. Mandatory ban phrases and player autonomy are not solved. Future audit needs critical-error rates per model and explicit qualitative severity, alongside ordinary preference averages.
4. **Next valid release gate:** independent previously unseen **40–60** held-out cases from at least **four entirely unused story/world components**, frozen before any new prompt tuning or model selection. Keep evaluation metrics and the rule for serious errors pre-registered, and compare Base / v0.1 / v0.2 under a deployment-appropriate, consistent prompt contract.

**Do not push private answer key or unredacted model responses as part of this metadata-only archival entry.** The reviewer CSVs were previously placed into a private Git repo by the owner; do not make the repo public without separate privacy review.
