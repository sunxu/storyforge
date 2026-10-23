# StoryForge R50 CPU46 — Owner private Tokenizer safe-aggregate intake

**Date:** 2026-10-23 (Asia/Singapore). **Evidence tier:** Owner-provided terminal output and count-only JSON pasted into conversation; original private 46-row report bytes were **not provided here** and were not independently parsed. No private prompts, case identities, or story text included. Source gate `R50_CPU46_OWNER_INTAKE_REPORT_HASHES_PASS__DRAFT_ONLY__NOT_FINAL_SEAL` is previously archived in `V03_R50_CPU46_OWNER_HF_JOB_INTAKE_SAFE_20261023.md`.

## Exact scope and reported source pins

- HF Job `6ada3f1d925af0e27d4f569f`, `adradar` CPU-only, run key `r50-cpu46-20261022T164410Z-305591`.
- Safe aggregate schema `storyforge-r50-cpu46-token-report-safe-aggregate-v1`; status `TOKEN_LENGTHS_EXTRACTED__DRAFT_ONLY__NOT_FINAL_SEAL`.
- Owner report `R50_CPU46_REPORT_SAFE_AGGREGATE_WRITTEN__DRAFT_ONLY__NO_JOB`, `R50_CPU46_TOKEN_LENGTH_STATISTICS=EXTRACTED`.
- Source intake receipt SHA256 `9b922c53cdafab11bd523e9c70f71a66a45d631da2b033487f2320b4150fe781`.
- Original private report SHA256 `56aeac340ac1c0be1d0000314bcbdc72abd2f59582d643eee9e50698529f748e`; Owner safe aggregator reports `private_report_sha256_verified=true`.
- `46` case records from a single collection labeled `cases`; numeric field `input_tokens`; `all_46_token_lengths_verified=true` in Owner aggregate.

## Actual pinned Qwen tokenizer, under DRAFT budget only

- `Qwen/Qwen3.8-27B` revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`, Transformers `5.16.1`.
- Draft max context `16,384`; draft reserved output `1,536`; resulting draft input limit `14,848` tokens.
- **46/46** within draft input budget; **0** over.
- Input token count: minimum `558`; median `1,362.0`; mean (rounded) `1,963.7`; nearest-rank P95 `4,265`; maximum `8,757`. Headroom at observed maximum: `6,091` input tokens, or `16,384 - (8,757 + 1,536) = 6,091` combined-context tokens.
- **Decision:** `R50_46_TRUE_QWEN_INPUT_LENGTH_BUDGET_REPORTED_PASS__DRAFT_ONLY`. This confirms the 46 original private report rows fit the **currently unapproved** budget, at Owner receipt verification level; **not** a final 4-arm generation/truncation contract.

## Gates that remain OPEN

- Historical `12` cases end in a User message followed by the new User input. This aggregate has `trailing_user_history_report_count=null`, `trailing_user_history_report_coverage=0`, `all_46_template_role_semantics_verified=false`. **No claim** of double-User role semantics.
- Semantic isolation from Train/Validation/development exposures, aliases, shared historical worlds/event clusters and temporal rule validity: **HOLD**.
- Exact model-arm parity and frozen four-arm role/rendering/truncation/sampling/grader contract: **DRAFT, NOT APPROVED**.
- Final protected evaluator bundle, answer-key/randomization custody, and formal test admission: **NOT SEALED / 0 ADMITTED**.
- No GPU, model inference, or training from this aggregate; R54 remains **NOT PROMOTED**.

**Next recommended CPU-only Owner action:** establish and independently verify the exact unmodified serialized User/Assistant role sequences for the 12 trailing-User cases against the frozen source and template, with a count-only report; do not silently coalesce User messages or mutate R50 originals. This is separate from tokenizer input budget PASS. Only then tackle independent cross-world semantic isolation and pre-registration. Avoid re-running paid HF Tokenizer for this summary.

**Status:** `R50_CPU46_OWNER_TOKEN_LENGTH_46_OF_46_DRAFT_PASS__ROLE12_HOLD__WORLD_SEMANTIC_HOLD__NO_FINAL_SEAL`.
