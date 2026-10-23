# StoryForge R55 Gold5 v2 — Owner-local 76-item blind arbitration preparation receipt

Recorded 2026-10-23 (Asia/Singapore). Evidence is a user-provided Owner terminal output and count-only JSON, not private review source inspection or independently rehashed files.

## Safe receipt

- Owner status: `R55_GOLD5_ADJUDICATION_PRIVATE_PACK_PREPARED__NO_CONFIRMED_EVENTS__NO_R50`.
- Schema: `storyforge-r55-gold5-event-arbitration-v1-safe-prep-v1`; scope `flagged`.
- Original developer source: 20 distinct exposed cases, 2 story worlds, original Gold as non-model historical reference, four model responses.
- `arbitration_items=76` unique flagged case-and-candidate groups; `selected_items_with_preexisting_flags=76`.
- `flagged_reviewer_case_arm_category_marks=327` individual reviewer-by-case-by-arm-by-category markings across Pair/Four/Five. **327 are not independent problems, validated severe events or error counts**.
- Each selected item must receive independent judgments for **both** categories (`agency`, `hard_fact_or_ban`); 76×2 = 152 verdict slots. This does **not** imply 152 distinct events.
- `blind_items_sha256=b97e743ba3901561dc5745f9f50a47e52d1199c7c60f106ad9d011604c741f65`.
- Owner-private `coordinator_index_sha256=3b0400a5629b6673c2317248f061b63e1a30c26d6486da81f7eb0636d7638e9a`, not uploaded.
- Source round freeze receipt SHA256s: Pair `ff1c81c39ff9983c64cc8cc43c68028e8e306a6bb28fd351eaabdd05f9af9747`, Four `664f4685c58c37fc817322aae523059e95da39df38e691384b28aac5394be506`, Five `2eb71a88f714226c10e45349067a1848650c20ea8a6211da7f45200f2c145bc0`.
- Original safe v2 prep SHA256: `6476da25e7d6b043a7bec3d413bfc75885c8571c188f318e3a4eb523888bdaa4`.
- Owner receipt explicitly: `adjudication_completed=false`, `model_source_reveal_to_arbitrator=false`, `gpu_job_started=false`, `model_promoted=false`, `r50_accessed=false`, `training=false`.

## Next gate: actual blinded human/event review, not another generation

Owner should distribute only the private reviewer files from `event-arbitration-v1/reviewers`: `R55_GOLD5_ARBITER_BLIND_ITEMS_PRIVATE.json` and the matching `R55_GOLD5_ARBITER_DECISIONS_BLANK_PRIVATE.json`, plus the case-level decision policy in `docs/R55_GOLD5_EVENT_ARBITRATION_OWNER_CN.md`. Never send `event-arbitration-v1/coordinator/R55_GOLD5_ARBITRATION_SOURCE_INDEX_PRIVATE.json`, model labels, previous ratings, outcome summaries, or previous unblind evidence. The arbitrator must not infer candidate identities.

For every candidate and each category, decide `CONFIRMED` (exact candidate_quote plus context_quote and rationale), `REJECTED` (grounded rationale) or `HOLD_INSUFFICIENT_EVIDENCE` (missing proof). A syntactically present quote is not proof that the quoted passage establishes a semantic failure. A single candidate may contain multiple independent events; only human adjudication can enumerate distinct events.

After the blind decision JSON is completed, run the already versioned local script `scripts/v03_r55_gold5_event_arbitration.py --mode validate --pack <event-arbitration-v1> --decisions <completed-private-json> --out-dir <unused-private-validation-dir>`. Expected SAFE receipt: `R55_GOLD5_ARBITRATION_DECISIONS_SAFE_COUNT_ONLY.json`, which includes verdict counts by arm and category with a strong warning not to treat selected flagged-case counts as unbiased model error rates. The validation script will not open R50 or run a GPU job.

Do not alter R55 frozen scores, original source/Git SHA, prior v0.3-A `NO_GO_FOR_PROTECTED_R50_NOW`, or R56 four-model+matched-original-Gold DRAFT. No R50 final test admission or model promotion follows from this preparation.

Status: `R55_GOLD5_V2_FLAGGED76_ARBITRATION_PACK_OWNER_PASS__152_CATEGORY_DECISIONS_PENDING__NO_R50`.
