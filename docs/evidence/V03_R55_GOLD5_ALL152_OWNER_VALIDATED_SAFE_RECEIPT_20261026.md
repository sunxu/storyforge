# StoryForge R55 Gold5 — All 152 category judgments: Owner-local format/quotation validation receipt

**Date:** 2026-10-26. **Evidence tier:** User-provided Owner-local count-only validator output, **not** independent review of complete private cases or semantic certification.

## Validation and frozen identity

- Tool status: `R55_GOLD5_FINAL_EVIDENCE_ALL_152_FORMAT_VERIFIED__NOT_SEMANTIC_CERTIFIED__NO_R50`.
- Source: 76 originally flagged candidate replies × 2 categories, total **152/152** completed category judgments; `not_reviewed_in_this_validation=0`.
- Original Owner docket SHA256: `60ffc85e0c7a327347315b0917da1256301344eb2f78af94ec0093904a70c813`.
- Completed Owner-assisted decision JSON SHA256: `d31b712778bef013b06b93cc457507643d9117db593840ae56609bf26c9f2523`.
- Private validator output SHA256: `7c231809fc009cd5035fafe46fada2cd41aa4d1be5f667dd31121da8c52ebeca`.
- First priority 65 subset had already passed; the complete 152 validation does not change the first 65 votes. Local form and exact quote verification does **not** establish semantic correctness or adjudicator independence.
- The user's checker emits `final_verdicts_are_human_owner_decisions_not_automated_vote_aggregation=true`. This field cannot substantiate human authorship: the 152 decisions were **AI-assisted drafts** produced in ChatGPT and then run through the Owner's Mac validator, with no separate documented Owner per-case human sign-off. Do not publish this as human-adjudicated ground truth.

## Count-only aggregate

| Source arm | Flagged candidates | CONFIRMED category slots | REJECTED category slots | HOLD category slots | Total category slots |
|---|---:|---:|---:|---:|---:|
| Base | 17 | 14 | 19 | 1 | 34 |
| Original Gold | 13 | 15 | 11 | 0 | 26 |
| v0.1 | 14 | 19 | 8 | 1 | 28 |
| v0.2 R46 | 16 | 16 | 15 | 1 | 32 |
| v0.3-A R54 | 16 | 15 | 16 | 1 | 32 |
| **Total** | **76** | **79** | **69** | **4** | **152** |

| Category | CONFIRMED | REJECTED | HOLD | Total |
|---|---:|---:|---:|---:|
| `agency` | 17 | 59 | 0 | 76 |
| `hard_fact_or_ban` | 62 | 10 | 4 | 76 |
| **All categories** | **79** | **69** | **4** | **152** |

- Four remaining HOLDs are all `hard_fact_or_ban`: one each in Base, v0.1, v0.2 and v0.3-A. Original Gold has no HOLD in the 13 flagged candidates.
- Neither 79 CONFIRMED category entries nor 76 candidate responses are a count of independent semantic error events. One response may contain multiple issues within a category; same response can trigger both categories. Source arms have unequal preselected/flagged candidate counts; there is **no population-wide model error rate** and no valid quality ranking from these figures.
- The `hard_fact_or_ban` umbrella also covers explicit character dialogue format requirements, restrictions on writing player mental/behavioral responses, and other story rules; don't equate all 62 with fictional chronology/fact hallucinations, nor exclusively literal forbidden-word violations.

## What is and isn't approved

- **PASS**: Frozen source/decision hashes match reported Owner local validation, 152 completed category records satisfy schema/quote-presence checks; 4 HOLD preserved.
- **Not verified**: semantic truth of AI-assisted verdicts, provenance and reviewer independence, case-specific subtype consistency, de-duplication of actual error events, distinct-character/world independent evaluation.
- **Pending**: exact evidence review of 4 HOLD; case-level spot audit of confirmed violations and disputed rule interpretations, plus a transparent Owner semantic sign-off. Optional: split `hard_fact_or_ban` into `explicit_banned_phrase`, `dialogue_format`, `player_behavior_or_psychology_rule`, `hard_world_fact_or_timeline` and `other_explicit_rule` for data-design use without overwriting frozen verdicts.
- **Unchanged**: R54 v0.3-A remains NO-GO for protected R50; R46 v0.2 remains development comparator; R50 has no formal admitted protected evaluation items, was not accessed in this run; `training=false`, `gpu_job_started=false`, `model_promoted=false`. Gold5 is a selectively flagged set on two previously exposed development worlds, so neither tuning nor generalization claims can use these counts as fresh held-out evaluation results.

**State:** `R55_GOLD5_ALL152_OWNER_FORMAT_PASS__79C_69R_4H__AI_ASSISTED_SEMANTIC_SIGNOFF_PENDING__R50_UNTOUCHED`.
