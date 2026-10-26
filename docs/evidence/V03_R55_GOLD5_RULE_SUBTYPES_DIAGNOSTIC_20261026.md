# StoryForge R55 Gold5 — supplementary hard-rule diagnostic subtypes

**Date:** 2026-10-26 (Asia/Singapore). **Source:** locally mounted, Owner-provided frozen private first-to-third evidence docket, original `76 × 2 = 152` AI-assisted verdict JSON, and previous locally validated all152 safe receipt. This document contains **no private story prose, evidence quotes, candidate tokens or identity mappings**.

## Source integrity and status

- Frozen Owner final docket SHA256: `60ffc85e0c7a327347315b0917da1256301344eb2f78af94ec0093904a70c813`.
- Frozen all152 AI-assisted verdicts SHA256: `d31b712778bef013b06b93cc457507643d9117db593840ae56609bf26c9f2523`.
- Existing verdicts unchanged: **79 CONFIRMED / 69 REJECTED / 4 HOLD** across 152 category decisions; `agency` 17 CONFIRMED, `hard_fact_or_ban` 62 CONFIRMED and 4 HOLD.
- New separate Owner-private subtype proposals SHA256: `2db36e8e1a5f54befded8f8b7daaa2cbe527dbdbdbfc02bc581db3ad000b79b2`, 62 proposed hard-rule primary labels + 4 HOLD evidence-gaps; **never commit it to GitHub**.
- New safe aggregate SHA256: `b569cf91fc178f847b24a95fc124d62855db4819404696ebc3cfa7e6d054a259`, status `R55_GOLD5_RULE_SUBTYPES_DIAGNOSTIC_SAFE_PASS__NO_FINAL_RECLASSIFICATION__NO_R50`.
- New read-only standard-library diagnostic verifier `v03_r55_gold5_rule_subtypes.py` and synthetic tests: **15/15 PASS**, then real read-only source SHA/76-token-order/152-status/62-label/4-HOLD audit **PASS**. Source+tests are provided as an independent ZIP artifact and are **not yet committed as repo code**. No new GPU, inference, training, R50 access or model promotion.

## Primary diagnostic subtype counts (mutually exclusive within existing 62 CONFIRMED hard-rule category records)

| Diagnostic label | Description | Count |
|---|---|---:|
| `player_psychology_or_intent` | Unauthorized player feelings, motivation, beliefs | 15 |
| `player_action_or_speech` | Unauthorized player action or dialogue | 11 |
| `user_event_continuity` | User's already-completed event overwritten or denied | 5 |
| `character_identity_or_relation` | Unfounded player identity/address fact | 1 |
| `world_timeline_age` | Hard age / biographical timeline contradiction | 2 |
| `forbidden_phrase_exact` | Verbatim forbidden expression | 4 |
| `forbidden_phrase_semantic` | Prohibited-phrase semantic variant, **human-check priority** | 3 |
| `forbidden_user_echo` | Explicit prohibition on repeating user wording | 6 |
| `forbidden_echo_question` | Prohibited same triggering phrase followed by question mark | 12 |
| `dialogue_language_format` | Story-specific mandatory Korean original/Chinese translation format | 3 |
| **Total** | **One primary label per existing confirmed category** | **62** |

This corrects a misleading previous field name: `hard_fact_mismatch` was a coarse validator enum, not a substantiated description of all these cases. Specifically, **26** cases primarily involve player psychology/action, **18** involve user echo/question forms, **7** involve forbidden literal/semantic expressions, **3** dialogue-language formatting, and **8** identity/timeline/event continuity. These figures remain candidate×category verdict classifications, not independent-world model failure rates.

**Four remaining HOLDs — retain:** ambiguous antecedent/unstated prior event (v0.3-A); undetermined bottle material/door mechanics and previous character naming (v0.2); NPC use of general ‘大嫂’ address and travel chronology (v0.1); semantic similarity threshold for an explicit banned phrase (Base). No other known facts support a safe final conversion. These notes are an aid to deciding whether *new* source evidence is necessary, not an instruction to re-adjudicate by speculation.

## Data/quality implications — proposals, not training authorization

1. Add explicitly matched-positive/negative examples that preserve player agency without treating **all** noncritical physical movements as severe agency violations. Retain the separate `agency` rubric vs hard no-ghostwriting rules.
2. Check repeated user-word and echo-question templates against the **specific story rule**; those prohibitions are not automatically global policies for every story.
3. Separate literal forbidden words from semantic equivalents; near-synonym labels require independent evidence spot-check before becoming automatic evaluator assertions.
4. Distinguish dialogue-format failure from world/age/relationship contradictions; add source-version and effective-time provenance when building factual examples.
5. Original Gold appears among flagged confirmed hard-rule items, so it must pass the same admission gate as generated candidates before being used as a new teacher.
6. A successor v0.3-B evaluation needs genuinely unexposed stories and preregistered tests; this old 20-question development set must not become claimed new heldout.

**Limitations:** All primary labels are **AI-assisted diagnostic proposals** derived from original quote/rationale and available context. Source validator checked literal consistency and counts, not independent semantic truth or whether the text was genuinely authored/reviewed by a human. The original AI-assisted 152 judgments remain frozen as a format-PASS record, pending transparent Owner semantic sign-off. HOLDs remain unresolved.

**Gate unchanged:** `R54_NO_GO__R46_COMPARATOR__R50_SEALED__NO_TRAINING__NO_PROMOTION`.
