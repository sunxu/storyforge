# StoryForge R55 Gold5 v2 — Owner real 20-case prep accepted; independent reviewers pending

Date: 2026-10-23 (Asia/Singapore). Evidence is Owner-provided terminal stdout and count-only JSON pasted in this conversation. Private original CSV bytes, original story texts and coordinator key were not uploaded or rehashed here.

## Real Owner-local v2 preparation

- Owner reported statuses: `R55_GOLD5_V2_20_EXACT_SOURCES_PASS__NO_OUTPUT__NO_JOB` and `R55_GOLD5_V2_THREE_DISTINCT_BLIND_TASKS_PREPARED__DEV_ONLY__NO_R50`.
- 20 reused exposed R47/R48/R55 development cases from 2 historical worlds; original Gold references 20, frozen four model responses 80.
- Three independently randomized task types: Pair (v0.3-A/v0.2), Four model-only, Five including anonymous Original Gold. Three pristine reviewer CSVs each; 9 CSVs total; reviewers_completed=0.
- Coordinator private-key SHA256 reported: `fc328688fac957c849d822d82db841479105afb0c885b48b381b1a270f9f3334`. No identity key was opened by this step.
- Owner-reported pristine Pair CSV SHA256 for each of 3 blank sheets: `5b991e66d017cd6ee125f0e936b300f3f1e64dfa80daeb54d4f2b4837bb0e33c`.
- Owner-reported pristine Four CSV SHA256 each: `625e5ff0c605243a1e68549001c3404c314f5f95568dd1d8428c402bceab12d6`.
- Owner-reported pristine Five CSV SHA256 each: `d072da7e96f7b57d7b56d1846f6202b989304b9b34c6080aa04ec6b22ddf8027`.
- Owner source report pins: v03 response `80586435b4b8dbe361d2e76d746a1e0e88154d08525d63720562810efa186557`; R55 source report `924404daa12ed5886a859e4445b7995350228f559995f646d480859f76c4fd64`; original compiled Test `d8eee6db5882d85dce7ffc01256e7c5b9b46e133bdb2cf8591259112b92e980d`.
- Explicit limitations: `new_heldout=false`, `final_seal=false`, `r50_accessed=false`, `gpu_inference=false`, `training=false`, `model_promoted=false`.

## Independent blind reviewers: next steps

1. **Release Pair sheets only** to 3 independent reviewers, one each, plus `docs/R55_GOLD5_V2_REVIEWER_PROTOCOL_CN.md`. Withhold Four/Five, existing R55/R48 scores, all source identity maps and model labels.
2. Once each reviewer has returned 20 rows of complete 6-axis scores, severe flags and evidence, freeze all 3 rated Pair CSVs. Expect 720 valid Pair rating cells.
3. Only after the Pair freeze, distribute model-only Four sheets; verify/freeze 1440 rating cells. Only after Four freeze, distribute Gold-anonymous Five sheets; verify/freeze 1800 rating cells.
4. Do not unblind any task before all desired blinded ratings are frozen. Same reviewers seeing all three variants may develop carryover effects; prior R48/R55 exposure must be disclosed. Three votes are not three independent test cases.

## Newly prepared privacy-safe local freeze tool (NOT run on real scores)

- Deliverable `StoryForge_R55_GOLD5_V2_FREEZE_TOOL_NOJOB_20261023.patch` SHA256 `67ddaaf2acefb44fd611b8f5f3485604ab173912f28de00928f4164cc7d2f3c1`.
- Deliverable `StoryForge_R55_GOLD5_V2_FREEZE_TOOL_NOJOB_20261023.zip` SHA256 `ba6bb1c91139e0a4dcf6ae7e90b73ab600bb960c7441f88b6ac1d7d32be4fe45`.
- Files: `scripts/v03_r55_gold5_review_freeze.py`, `tests/test_v03_r55_gold5_review_freeze.py`, `docs/R55_GOLD5_V2_REVIEW_FREEZE_OWNER_CN.md`.
- 25/25 synthetic tests passed; patch applied successfully in separate synthetic Git repository and 25/25 tests passed again. Git source files not individually pushed in this action.
- Tool validates pristine-source SHA against the Owner safe preparation receipt, exact row/source preservation, valid 1–5 scores, allowed preferences/flags, required evidence, distinct completed reviewer bytes; it archives verified scored CSVs outside Git with read-only permissions and emits count-only freeze receipt. Does not open the identity mapping or R50. Syntactic PASS is not semantic-review correctness/independence approval.

Existing R55 `NO_GO_FOR_PROTECTED_R50_NOW` stays unchanged. R50 formal admitted 0, no final seal, no model promotion, no new HF/GPU Job.

Status: `R55_GOLD5_V2_OWNER_PREP_REPORTED_PASS__PAIR_REVIEWERS_PENDING__FREEZE_TOOL_SYNTHETIC_PASS__NO_R50`.
