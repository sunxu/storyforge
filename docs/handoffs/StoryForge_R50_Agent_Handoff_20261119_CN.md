# StoryForge R50 — New-agent handoff packet (2026-11-19)

**Repository:** `sunxu/storyforge`  
**Current handoff branch:** `docs/r50-agent-handoff-20261119`  
**Current taskbook:** `docs/r50/R50_46_PRESEAL_TASKBOOK_20261119_CN.md`  
**Copy/paste prompt:** `docs/prompts/StoryForge_R50_New_Agent_Prompt_20261119_CN.md`  
**Latest audit receipt:** Draft PR #32, not merged.

**Handoff publication:** This packet and the current taskbook/prompt are proposed in [Draft PR #33](https://github.com/sunxu/storyforge/pull/33), branch `docs/r50-agent-handoff-20261119`. The latest audit receipt is separately proposed in [Draft PR #32](https://github.com/sunxu/storyforge/pull/32), branch `docs/r50-world-cpu46-audit-20261119`. Fetch the relevant branch files explicitly; do not assume either PR is already in `main`.

## 1. Mission

Take over the remaining R50 46-case protected Held-out gate work. The immediate task is evidence reconciliation and closure of the outstanding temporal-provenance and semantic-world graph gates. Do not restart completed audits. Do not turn this into training, model tuning, broad R60 work, or a fresh dataset search.

Read the current taskbook first. It is the operational source of truth for work ordering and no-repeat rules.

## 2. Repository / PR state at handoff

- Repository default branch: `main`.
- Latest 2026-11-19 audit document is proposed in [PR #32](https://github.com/sunxu/storyforge/pull/32), branch `docs/r50-world-cpu46-audit-20261119`.
- PR #32 adds one Markdown evidence file: `docs/evidence/V03_R50_WORLD_CPU46_ROLE12_AUDIT_20261119_CN.md`.
- PR #32 is Draft/Open and unmerged. Do not assume it is on main.
- PR #32 GitHub Actions CI run `44371884201` failed in the repository-wide Ruff step with 202 findings in pre-existing Python files. Tests and evidence-integrity steps were skipped. The PR diff is documentation-only. Do not expand this task into a repository-wide Ruff cleanup.
- This handoff is documentation/evidence coordination. It does not authorize merging PR #32 or any protected-data operation.

## 3. Current gate summary

| Gate | State |
|---|---|
| Full source bytes / scoped inventory | Owner reports checked |
| Old06_15 CRC / Old14 CRC | PASS |
| 50 source-pair rows | Checked |
| Same Story ID pairs | 0 |
| Extra archive Source-ID conflicts with R50 | 0 |
| Exact long-message and sampled lexical flags | 3 pair rows |
| Prior W17 AI pair adjudication | Same three pairs; all `INSUFFICIENT_EVIDENCE`; reviewer independence not script-verified |
| Seven W17 full-message gaps | All `INSUFFICIENT_CONTEXT` |
| Timepoint card/rule actual inference proof | PENDING / NOT CERTIFIED |
| Hidden alias / event / transitive world closure | HOLD |
| CPU46 token lengths | 46/46 within Draft budget |
| ROLE12 structure | 46/46 roles/order; 12/12 trailing User encoding reported |
| Consecutive User policy | APPROVED on 2026-11-19; runtime parity still unverified |
| Four-arm runtime parity | NOT VERIFIED |
| Official Held-out admission | 0 |
| Final Seal | NOT PERFORMED |

## 4. Exact no-repeat instructions

Do not:
- rerun Old06_15 or Old14 CRC checks;
- repeat the 50-pair lexical scan against the same pinned source bytes;
- repeat the same three W17 pair AI reviews or seven full-message gap reviews without genuinely new source provenance;
- rerun the CPU46 tokenizer job for the same frozen 46 inputs;
- rerun `scripts/v03_r50_role12_owner_audit.py` against the same inputs/report absent a concrete mismatch;
- ask the Owner again whether the intended story worlds are independent; the 2026-10-23 attestation is already recorded and is not a substitute for independent proof;
- blindly execute the older 2026-10-22 R45 full-history isolation command. First reconcile whether the 2026-11-19 inventory already covers its source scope and exact SHA-pinned inputs.

## 5. Sequenced next work — do not launch four parallel audits

1. **W1 first:** complete the historical evidence coverage crosswalk between the 2026-11-19 inventory, W17 dossiers, source/archive manifests, frozen R45 scope and known transitive-link records. Decide `NEW_EVIDENCE_PRESENT` or `NO_NEW_EVIDENCE`. This is the prerequisite for any new semantic adjudication.
2. **W2 may run in parallel with W1:** read-only search existing Owner-held historical card/version snapshots, prompt-assembly/runtime records and long-term rule versions. Record searched locations and artifact availability. If absent, record `SOURCE_UNAVAILABLE` / `HOLD`; do not reconstruct history or initiate new export work.
3. **W3 only on a trigger:** if W1 or W2 identifies genuinely new provenance relevant to a specific unresolved edge, propose a narrowly scoped adjudication of only that edge. If no new provenance exists, mark W3 `NOT_TRIGGERED`; do not repeat the three W17 pair reviews or seven full-message reviews.
4. **W4 separate gate:** the Owner explicitly approved the exact consecutive-User contract on 2026-11-19. Perform only read-only Base/v0.1/v0.2/v0.3-A runtime role/template parity verification using already-existing Owner-local receipts/configuration. Do not rerun the structural/tokenizer audit or mutate frozen messages.

   > 12 条历史末尾的 User 消息与新追加的 User 消息，是两条独立的连续 User turn。四个模型臂均原样保留两条消息，不合并、不改写、不删除，并将其作为统一输入合同的一部分。

   Policy is now `ROLE12_POLICY = APPROVED`; this does not mean four-arm runtime parity passed.
5. Prepare preregistration only after the gates close. No final seal or inference without separate Owner authorization.

No HF Job, paid tokenizer job, GPU, model inference or training is needed or authorized for this handoff. If W1 finds no new evidence, preserve HOLD instead of generating another review that cannot change the decision.

## 6. Required first response from the new agent

Before making changes, report:
- current `main` HEAD and current state of PR #32;
- which cited artifacts were actually fetched and read;
- a no-repeat matrix marking each completed task;
- the W1 crosswalk result, the existing-source locations searched for W2, the W3 trigger condition, the approved ROLE12 policy, and the still-unverified four-arm runtime parity;
- whether any proposed operation would access private R50 content, paid HF, GPU, inference, training or frozen inputs.

Do not ask the Owner to repeat information already in this packet. Ask only for the specific missing evidence or authorization after repository and artifact checks are complete.

## 7. Privacy and execution boundary

- Raw R50 candidate JSONL, story text, target replies, case IDs, source-message IDs, private source mappings, answers and per-case tokenizer rows remain in the Owner-controlled private environment.
- GitHub receives only sanitized aggregate receipts and evidence pointers.
- Source inspection, if later authorized, is Owner-local and read-only. Return only allowlisted aggregate SAFE output.
- No database writes, source mutation, prompt rewriting, role coalescing, truncation, GPU, paid HF Job, model inference, training, answer-key access, final seal or promotion.
- Keep R50 separate from R56/R60 development, Base336 and other evaluation workstreams unless the Owner explicitly expands scope.

**Handoff state:** `R50_W1_CROSSWALK_DONE__W2_SOURCE_UNAVAILABLE_IN_SEARCHED_SOURCES__W3_NOT_TRIGGERED__W4_POLICY_APPROVED_RUNTIME_PARITY_PENDING__NO_FINAL_SEAL`.


## 8. Execution update — 2026-11-19

W1 and W2 were executed as documented in `docs/evidence/V03_R50_W1_W2_COVERAGE_CROSSWALK_20261119_CN.md` (original crosswalk commit `3e7ea1266b4101fec6470f5e4ee1171de6ca7988`; later Owner rank-pair and supplementary Gold lookup updates are recorded in the same file).

- W1: `NO_NEW_EVIDENCE__EXISTING_W17_FLAGS_RECONFIRMED`; W3 is `NOT_TRIGGERED`.
- W1 rank-pair follow-up: Owner supplied `transitive_known_old_link=[4,7]`; both values are verified old-source ranks, with 4 in frozen R45 and 7 outside it. This is consistent with the previously recorded old 04→07 edge; the two array elements are endpoints, not two edge objects. Old rank 4 ↔ R50-17 reproduces the already-reviewed W17 lexical/exact flag (5 sampled matches, 1 long exact); old rank 7 ↔ R50-16..20 has zero reported matches. No new semantic evidence; the possible transitive path to W17 remains `INSUFFICIENT_EVIDENCE`, W3 `NOT_TRIGGERED`.
- W2: `SOURCE_UNAVAILABLE_IN_SEARCHED_SOURCES` for actual inference-time card/rule snapshots and prompt-assembly/runtime receipts. The search covered the GitHub source tree and available R50 Library artifact inventory, not every possible Owner-held storage location.
- W4 policy is explicitly approved; four-arm runtime parity remains unverified and is limited to read-only evidence inspection.
- No repeated source/CRC/lexical/AI/tokenizer/ROLE12 audit; no HF Job, GPU, inference, training, answer-key access, admission, or seal.


## 9. Owner decision and Original Gold comparison update — 2026-11-19

Owner explicitly approved the exact consecutive-User contract:

```text
ROLE12_POLICY = APPROVED
CONSECUTIVE_USER_SEMANTICS = TWO_INDEPENDENT_USER_TURNS
MERGE_USER_MESSAGES = false
REWRITE_USER_MESSAGES = false
DELETE_USER_MESSAGES = false
APPLY_TO_ALL_FOUR_ARMS = true
```

The policy approval does not establish actual runtime parity. W4 now proceeds only as a read-only comparison of already-existing Base/v0.1/v0.2/v0.3-A runtime/load/config evidence. If such historical evidence is absent, record `SOURCE_UNAVAILABLE`; do not start a model or tokenizer job.

The Owner also clarified that the original answer must be included in comparison. The R50-specific contract is:

`docs/plans/V03_R50_FOUR_MODEL_PLUS_ORIGINAL_GOLD_CONTRACT_20261119_CN.md`

It defines **four model arms + Original Gold** as a five-way comparison only when the historical original Assistant reply is authenticated for the exact same current User input, full preceding history, System/Card/Rules cutoff and source bytes. R50 is prompt-only in the existing source schema, so Original Gold coverage is not established for all 46. Report five-way results only on the exact-match subset and report `N_gold / 46`; keep unmatched cases in the four-model denominator. Never substitute a similar story reply, Gold195, later edit, or new human answer as Original Gold. Any separately authored answer must be called `NEW_HUMAN_REFERENCE` and requires separate approval.

The contract requires anonymous per-case randomization, three independent reviewers, six dimensions, a separate frozen v0.3-A vs v0.2 direct pairwise comparison, case-level serious-error adjudication and world-clustered uncertainty. It does not authorize R50 inference, scoring, Final Seal or promotion.

**Current status:** `ROLE12_POLICY=APPROVED`; `FOUR_ARM_RUNTIME_ROLE_PARITY=NOT_VERIFIED`; `ORIGINAL_GOLD_R50_COVERAGE=NOT_ESTABLISHED`; all world/timepoint gates remain unchanged.


## 10. W4 implementation inventory — 2026-11-19

The read-only GitHub source inspection found:
- R47 has a historical three-arm runner (Base/v0.1/v0.2) for exposed old prompts; its parameters are not proof of R50 four-arm effective runtime settings.
- R55 has an offline five-answer blind-pack builder that consumes already-existing outputs and does not run inference or access R50.
- R54 has a one-candidate training/adapter-reload runner, not a four-arm parity run.
- The R50 ROLE12 local auditor validates Draft structure/Tokenizer alignment and explicitly leaves actual four-arm runtime parity false.

No R50-specific four-arm inference runner or actual four-arm load receipt was found in the inspected GitHub source tree. Owner has authorized read-only inspection, but the current chat has no direct Owner Mac filesystem connector. The next evidence request must therefore be limited to already-existing per-arm load/config/runtime records or a count-only SAFE receipt derived from them. If unavailable, mark `SOURCE_UNAVAILABLE`; do not start any model/job to create evidence.


## 11. Existing static input receipt and Original Gold inventory

The R50 Library contains the 2026-10-16 deep triage report with a shared static Draft message-sequence SHA256 `9ad0254f740a979e9b79b458a22e61e40db4ff98fb946e0332cf172e6888565c` for 46 cases / 364 historical messages / 12 trailing User→User sequences. The report explicitly does not claim tokenizer input-ID parity or actual four-arm runtime execution. Do not repeat its static construction check.

The searched R50 Library directory inventory has 106 entries, including frozen candidate/provenance, W17 review packets, CPU46 and ROLE12 receipts; no dedicated R50 Original Gold reply package was found in that bounded inventory. This does not exhaust every Owner-held source. Keep `ORIGINAL_GOLD_R50_COVERAGE = NOT_ESTABLISHED_OUTSIDE_EXAMINED_SOURCES` until exact same-prompt/history/cutoff original Assistant replies are authenticated.


## 12. Original Gold source availability update

See SAFE receipt: `docs/evidence/V03_R50_ORIGINAL_GOLD_SOURCE_AVAILABILITY_20261119_CN.md` (commit `0c0bec3e4dc495ce35e49c2e59b446c637a78c0c`). Owner-provided output verifies both local 14-chat archive copies are byte-identical and match expected size/SHA256/ZIP CRC; the 06–15 archive also matches expected size/SHA256/ZIP CRC. The agent did not independently access the Owner Mac files, so these remain Owner-reported local verification.

The pinned R50 source replay has already established zero normalized verbatim reuse between the 50 new User inputs and User messages in the five pinned R50 source transcripts. Therefore no protected 46 case can obtain an exact same-input Original Gold from those five transcripts (`0/46` within that pinned source scope). This does not prove zero across every possible Owner-held archive: the 14-chat and 06–15 archives have not been searched for exact full-history matches. Do not treat a text-only match in another story as Original Gold.

The four historical W17/source-overlap scripts are absent from the current checkout but exist on `audit/r49-r50-source-intake-20261015`. They are historical audit code, not a missing Original Gold matcher; do not switch branches or rerun completed CRC/lexical/W17 work merely to recover them. Overall `ORIGINAL_GOLD_R50_COVERAGE = NOT_ESTABLISHED`. Any next lookup must compare exact current User input plus complete preceding history and cutoff context, and emit aggregate counts only.


## 13. Supplementary archive scope reconciliation

See SAFE receipt `docs/evidence/V03_R50_ORIGINAL_GOLD_SOURCE_AVAILABILITY_20261119_CN.md` (follow-up commit `fea7d2e1b15375b631d24ad650b545ec7174d889`). The 14-chat archive yielded 14 actual conversations plus 14 AppleDouble metadata entries; the 06–15 archive recursively yielded 1,010 conversations. The Owner-run content and ID-first scans found no exact history/provenance matches in either archive. They are supplementary historical collections outside R50's five pinned source worlds 16–20; zero matches there are expected and do not challenge the authoritative 392/392 replay.

No same-current-User Original Gold is eligible from the five pinned R50 source transcripts (`0/46` within that scope), because the source replay found zero normalized verbatim reuse across all 50 new User inputs. Overall Owner-wide coverage remains `NOT_ESTABLISHED` outside examined sources. Do not rerun completed scans. Use four-model comparison for cases without Gold; never treat the next historical Assistant turn as an answer to the appended new User input.


## 14. Historical R48/R55 comparison precedent found — 2026-11-19

Read-only GitHub inspection found the historical answer-review workflow needed as a design reference:

- R48 compares four answers: Original Gold + Base/v0.1/v0.2. It is not four models.
- R55 specifies five answers: Original Gold + Base/v0.1/v0.2/v0.3-A, with exact-source checks, anonymous five-way and separately randomized v0.3-A-vs-v0.2 pairwise tasks. This is a development-only reuse of 20 exposed prompts from two worlds; its real Owner-local preflight was pending in the 2026-10-23 receipt.

This is useful prior implementation, so do not redesign or duplicate the reviewer pack. It does not establish R50 Original Gold coverage or actual R50 runtime parity. Keep W4 NOT_VERIFIED until pre-existing R50-specific runtime/load evidence is found. Do not execute R48/R55 build scripts on R50 data.


### Later R55 Gold5 v2 outcome (Owner aggregate, development-only)

The subsequent Owner-unblind SAFE aggregate is documented at docs/evidence/V03_R55_GOLD5_V2_OWNER_UNBLIND_DECISION_20261023.md. It reports 20 exposed prompts across two worlds, three reviewers and 3,960 Pair/Four/Five ratings. Pair v0.3-A vs v0.2 was 10:10 with v0.3-A lower on all six axes; five-way means were Original Gold 3.500, v0.2 3.461, v0.3-A 3.197. The Owner decision retained v0.2 and marked R54 checkpoint-16 NO-GO for R50. Treat this as Owner-pasted development aggregate only: reviewer independence was not technically certified, hard-event adjudication remained pending, and it says nothing about R50 unseen-world performance.


## 15. Owner-local inventory correction and R55 evidence-resolution chain — 2026-11-19

Owner later supplied `transitive_known_old_link=[4,7]` and rank arrays: both are old-source ranks, with 4 in frozen R45 and 7 outside R45. The two values are consistent with the previously recorded 04→07 rank pair and represent endpoints, not two edge objects. The possible transitive path from this old component to W17 remains `INSUFFICIENT_EVIDENCE`.

The Owner-local R55 inventory includes first arbitration, second and third evidence audits, and a final 152-category decision file. The public R55 protocol defines 76 flagged candidate replies × two categories (152), with P0=65/P1=87; third audit covers 46 selected replies / 92 slots and includes the 59 original disputed/first-HOLD categories. The third-audit report explicitly prohibits automatic majority resolution and says reviewer independence was not technically verified. The final-evidence protocol distinguishes format/quotation validation from semantic certification. Do not treat private-file existence as proof of a successful final gate; request only the five safe count-only receipts next.

R50 W4 policy was subsequently approved by the Owner on 2026-11-19. The 2026-10-23 Role12 receipt predates that approval and correctly records the policy as not yet approved at the time; its `actual_four_arm_runtime_role_parity_verified=false` remains current because no later per-arm runtime evidence was found. Tokenizer draft-fit evidence is not deployed per-arm parity. No protected R50 admission, sealing, inference or GPU action is authorized.


## R55 safe-receipt update — 2026-11-19

Owner supplied all five safe count-only receipts. The first arbitration receipt validates 76 flagged candidates × 2 categories (syntax/exact quotations only; reviewer independence unverified; no R50). The second audit validates 68 candidates / 136 category decisions; 44 categories were mutually CONFIRMED by the first two arbiters and 59 were disagreement or first-HOLD categories requiring third review. The third audit validates 46 candidates / 92 category decisions, including the 59 original unresolved categories; it explicitly does not perform automatic final adjudication and does not technically verify reviewer independence.

The Owner's final evidence safe receipts now show:
- Priority P0: 65 category judgments; 38 CONFIRMED, 4 HOLD_INSUFFICIENT_EVIDENCE, 23 REJECTED; 87 were not yet included in that staged validation.
- All 152: 79 CONFIRMED, 4 HOLD_INSUFFICIENT_EVIDENCE, 69 REJECTED; `not_reviewed_in_this_validation=0`; status `R55_GOLD5_FINAL_EVIDENCE_ALL_152_FORMAT_VERIFIED__NOT_SEMANTIC_CERTIFIED__NO_R50`.
- P1 derived by subtracting the P0 receipt from the all-152 receipt: 41 CONFIRMED, 0 HOLD, 46 REJECTED across 87 slots. This is arithmetic over the two count-only receipts, not a separately emitted P1 report.

This closes the **mechanical completion/format-and-quotation validation** of all 152 originally flagged category slots, but it does NOT establish independent reviewer blinding, semantic correctness, or an unbiased model-wide failure rate. Four final Owner decisions remain HOLD for insufficient evidence. R55 remains development-only; R50 was not accessed, no GPU/training started, and no model promoted. Do not spend the protected R50 holdout based solely on these receipts.

W1 rank-pair follow-up: Owner supplied `transitive_known_old_link=[4,7]` and rank arrays establishing both as old-source ranks. This is consistent with the existing 04→07 rank pair, not two edge objects. Old rank 4 ↔ R50-17 is the already-reviewed W17 flag; old rank 7 has zero reported sampled/exact matches against R50 ranks 16–20. The possible transitive path to W17 remains `INSUFFICIENT_EVIDENCE`; no new source-backed provenance has triggered W3.


## 10. Owner rank-pair clarification — 2026-11-19

The Owner supplied the rank arrays and pair rows. `transitive_known_old_link=[4,7]` contains two old-source rank endpoints; it is consistent with the existing 04→07 edge and is not a count of two edge objects. Rank 4 is in frozen R45; rank 7 is an additional checked old source outside R45. The old-rank-4 ↔ R50-rank-17 result is the already-reviewed W17 flagged pair, while old rank 7 has no reported sampled/exact matches against R50 ranks 16–20. These limited matches do not alter the prior semantic `INSUFFICIENT_EVIDENCE` result, do not prove world independence, and do not establish a transitive path to W17. No repeated scan or adjudication is authorized or needed absent genuinely new provenance.


## 11. Supplementary archive lookup and CI follow-up — 2026-11-19

The Owner's corrected parser classified and skipped the 14 AppleDouble metadata entries in the 14-chat archive; all 14 actual conversations parsed (62,583 messages). The 06–15 archive parsed recursively as 1,010 conversations (71,884 messages). The exact-history lookup reported no exact 32-message history matches; the Message-ID-first diagnostic returned no positive match counts. This closes the bounded supplementary-archive lookup; do not rerun on unchanged bytes.

PR #33 CI for head `e95da034bde9d064082dcfa32908ebd1290ec6b5` completed failed at repository-wide Ruff (202 findings); tests and evidence-integrity steps were skipped. No R50 code change was made. The taskbook records this as pre-existing repository-wide lint debt, outside the authorized scope.


## 12. W4 partial runtime evidence — 2026-11-19

Read-only GitHub and Library inspection found these existing precedents:

- **R47 Base/v0.1/v0.2 runner:** `scripts/v02_r47_eval_runner.py` on `main` (blob `a2fa43f65b7b31631976cab1ac84b2b183b5f352`). It uses one shared `swift infer` path with the pinned Qwen revision, Transformers backend, BF16/BNB 4-bit, `max_new_tokens=1536`, `seed=42`, `data_seed=42`, `temperature=0`, and no validation shuffle. Adapter weights are SHA-guarded. This is old exposed-test runtime precedent, not an R50 46-case execution.
- **R55 v0.3-A inference:** Owner-local run directory `~/.local/share/storyforge/r55/inference-results/r55-dev-20261022T023436Z-188604/`; SAFE report confirms 20 outputs, R54 checkpoint-16 adapter SHA `121ec8...`, Qwen revision `1d4bf0f...`, ms-swift 4.5.3 / Transformers 5.16.1 / bitsandbytes 0.50.2, and generation values `temperature=0`, `seed=42`, `data_seed=42`, `max_new_tokens=1536`, `validation_shuffle=false`. The local runner and 243,541-byte runtime log are inventoried at `~/.local/share/storyforge/r55/one-shot-inference-20261022/scripts/r55_gpu_infer_runner.py` and `.../R55_R54_INFERENCE_RUNTIME_PRIVATE.log`, but their effective backend/template/stop/truncation details have not yet been extracted in this pass.
- **R50 draft receipt:** 46/46 role/order structures and 12/12 trailing-User tokenizer records are reported, but `actual_four_arm_runtime_role_parity_verified=false`. The old `trailing_user_interpretation_policy_approved=false` field predates the Owner's later explicit policy approval; current policy status is APPROVED.
- **Cross-backend warning:** the separate R53 CPU40 report recorded Transformers vs ms-swift input-token differences on 31 Train + 9 Validation rows. This is not R50 evidence, but it prevents assuming that the R50 Transformers-only draft receipt proves ms-swift serving parity.

W4 remains `NOT_VERIFIED`. The smallest next action is a read-only extraction from existing R47/R55 reports, R55 runner/contract/runtime log, emitting only hashes and allowlisted runtime flags. Do not emit prompt/response text, IDs, mappings, answer keys or full logs; do not rerun jobs or launch tokenizer/HF/GPU/inference.


## 16. Owner-local Runner inventory results — 2026-11-19

Owner supplied a read-only allowlisted extraction from existing local R47/R55 files. Local SHA256 values: R47 Runner `97270d6146a3a8ae8f1a2bf66b409bf26aba04735229e9b340f535435bbf6bae`; R47 report `9b5066004234e4140b9a6025843f836e2be22e8a3af61f8ab1a9340b9f93e253`; R55 Runner `f318bd318d818e4ccd1f9e2ec5a81252291c5e13d5084afb241ae99d89cbceb6`; R55 contract `1d500f48360f46e2d8ff2c9ab89ba4620a67af3e95761c8cda64817d7e440b64`; R55 report `924404daa12ed5886a879e4445b7995350228f559995f646d480859f76c4fd64`; R55 intake `a8569b96dc8a655dbc79046b0b24128cb459d8c9c1323f9806aecaa6fcfdd158`; R55 runtime log `f83f877441c38fbb1ef705a8b2e6acd0a4603bd14fcdd280741fe9e905cdfee3` (243,541 bytes).

Both Runner sources have identical extracted explicit settings: HF=true, Transformers backend, BF16, BNB 4-bit, BNB compute BF16, max_new_tokens=1536, seed/data_seed=42, temperature=0, validation shuffle=false. Neither source explicitly mentions `enable_thinking`; no explicit template/truncation/EOS/stop/context/top_p/top_k/repetition flags surfaced in this extraction. This proves matching source-level explicit settings only, not effective defaults or per-case R50 runtime parity.

R47 report says Base/v0.1/v0.2 generation completed for 20 old exposed prompts. R55 report says v0.3-A (R54 checkpoint-16) generation completed for 20 exposed prompts. R55's contract status `ONE_PAID_GPU_INFERENCE_AUTHORIZED_NOT_STARTED` is the pre-run contract; the later report and Owner intake show the run completed. The log extraction searched only a literal `COMMAND:` marker and found none; do not interpret that as an empty/uninformative log.

Current W4: `PARTIAL_HISTORICAL_RUNNER_CONFIG_MATCH__R50_RUNTIME_PARITY_NOT_VERIFIED`. Next action is a field-oriented SAFE scan of the existing 243,541-byte R55 log and both Runner sources for template, thinking, truncation, context, EOS/stop, sampling and role-sequence evidence. Print only allowlisted values, booleans and line numbers; never raw lines, prompts, responses, case IDs or mappings. If absent, record `NOT_RECORDED`. No new model/tokenizer/GPU/HF execution.


## 17. R55 effective runtime-log field scan — 2026-11-19

The Owner supplied a second SAFE field-oriented scan of the existing R55 runtime log (243,541 bytes; SHA256 `f83f877441c38fbb1ef705a8b2e6acd0a4603bd14fcdd280741fe9e905cdfee3`). It records effective runtime fields: Transformers backend, HF=true, BF16, BitsAndBytes 4-bit, `template=qwen3_8`, `template_backend=swift`, `enable_thinking=None`, `truncation_strategy=delete`, `max_length=262144`, `max_model_len=None`, `max_new_tokens=1536`, temperature 0, data_seed 42, validation shuffle false, and stop/stop_words fields present but their values withheld. EOS token ID was not found.

Important ambiguity: `seed=42` appears in invocation/runtime configuration records (lines 399/410), while a separate GenerationConfig-like record at line 4502 reports `seed=None`, `top_p=None`, `top_k=None`, and `repetition_penalty=None`. Do not silently collapse these records; the scope and precedence need an existing-record-only explanation. `enable_thinking=None` does not prove thinking disabled. `max_length=262144` is a logged max_length setting; `max_model_len=None` does not establish the effective context limit. Stop values remain private. The single `messages` marker at line 4512 does not prove consecutive User role preservation or per-case input-ID parity.

R47 and R55 Runner sources have matching explicit core CLI settings, but R47's source-only scan did not resolve its non-scalar revision expression and no R47 effective runtime log was supplied. Do not project R55's template/truncation settings onto R47.

**W4 status:** `PARTIAL_R55_EFFECTIVE_RUNTIME_FIELDS_FOUND__FOUR_ARM_R50_ROLE_PARITY_NOT_VERIFIED`. Remaining evidence: clarify seed/config record scope; effective behavior of thinking=None; corresponding R47 effective template/truncation/stop evidence if already recorded; and any existing evidence that two consecutive User roles survive the actual runtime serialization and per-case input assembly. Missing evidence is `NOT_RECORDED`; no model/tokenizer/GPU/HF execution is permitted to manufacture it.


Latest PR #33 CI after the R55 effective-runtime evidence update: head `cc9f68aaddc97442ff149cffa5f17f3729b78024` completed failed at repository-wide `ruff check .` with 202 findings; Tests and evidence-integrity stages were skipped. This is the known repository-wide lint blocker, not a new R50-specific failure. Keep this PR documentation-only.


## 18. R47 runtime-log filename search — 2026-11-19

Owner's recursive filename search in `~/.local/share/storyforge/r47/r47-20261014T091647Z-637890/` for `*.log`, `*runtime*`, `*launch*`, and `*command*` returned `MATCHED_FILES: 0`. Treat this strictly as no matching filenames in the searched directory, not as evidence that R47 did not execute or that all runtime metadata is absent. Known R47 artifacts remain `R47_PRIVATE_RUN_REPORT.json`, `R47_LOCAL_INTEGRITY_PASS.json`, `coordinator/private/R47_AUDIT_SUMMARY.json`, and `base-results.jsonl` / `v01-results.jsonl` / `v02-results.jsonl`. Next action is a safe read-only field scan of the existing JSON reports for runtime/template/truncation/stop/sampling metadata. Never emit raw prompt/response text, case IDs or private mappings. If not recorded, state `NOT_RECORDED`; no R47 rerun, model load, tokenizer, GPU or HF job.

## 19. R47 execution.log recovery lead — 2026-11-19

GitHub source verification established that the R47 Runner explicitly creates out/execution.log and writes command lines plus merged process output there. Its output root is evaluation-runs/v02-r47/<RUN_KEY>/. The historical collection script omits this log: it fetches the report, three result JSONLs, blind package, reviewer CSVs, private answer key and audit summary, but never execution.log. This explains why the Owner's local filename search returned zero without proving that the remote log was never produced.

Relevant exact runs:
- resumed three-arm run: r47-20261014T091647Z-637890; Base was byte-exactly reused, so this log should cover v0.1/v0.2 inference but not original Base generation.
- earlier Base run: r47-20261014T082109Z-820409; its log, if retained, is the source to inspect for actual Base inference.

Runner source SHA: a2fa43f65b7b31631976cab1ac84b2b183b5f352. Collector source SHA: 20150d94fd460d8551838a7d7da4cae8137d2ff1.

Next: Owner can perform a read-only hf buckets cp of only the two exact execution.log paths to a private temp directory; do not fetch any answer key, prompt, response or mapping artifacts. Parse locally and output only allowlisted runtime settings and line numbers. Missing remote object means SOURCE_UNAVAILABLE; no GPU/model/tokenizer execution is permitted.
## 20. R47 execution logs downloaded — 2026-11-19

Owner reports both exact remote `execution.log` objects downloaded successfully to the private local recovery directory:
- Base run `r47-20261014T082109Z-820409`: 84,617 bytes; SHA256 `34d3e33ca1888dbc1c61cf65c0f2619ebf41bae626deea131564db8e6a927399`.
- Resumed three-arm run `r47-20261014T091647Z-637890`: 450,504 bytes; SHA256 `18b077671b38404ff4821c4d9fb0342b3cb9430fc5d5565c9efc1586a4c3ab7c`.

These are Owner-reported local file hashes; runtime configuration is not yet established. Next use a local allowlisted parser to extract only runtime parameter values and line numbers. Do not paste raw logs or commit them. The resumed run reused Base, so only its v0.1/v0.2 portions are relevant to adapter runtime; the original run is the Base evidence.
## 21. R47 three-arm runtime logs parsed — SAFE aggregate (2026-11-19)

Owner provided local allowlisted-parser output only; raw logs and all prompt/response/private identifiers remain private.

- Base log: 84,617 bytes, SHA256 `34d3e33ca1888dbc1c61cf65c0f2619ebf41bae626deea131564db8e6a927399`, 1,183 lines; Base inference command at line 395 has no adapter.
- Resumed log: 450,504 bytes, SHA256 `18b077671b38404ff4821c4d9fb0342b3cb9430fc5d5565c9efc1586a4c3ab7c`, 8,676 lines; adapter inference commands at lines 395 and 4537.
- Runner source SHA `a2fa43f65b7b31631976cab1ac84b2b183b5f352` confirms arm loop order Base, v0.1, v0.2 and reuses earlier Base on resumed run; therefore resumed line 395 = v0.1 and line 4537 = v0.2.
- All three commands match: HF Transformers, BF16, BNB 4-bit, BNB compute BF16, max_new_tokens 1536, seed/data_seed 42, temperature 0, no dataset shuffle.
- Runtime fields match: `qwen3_8` / `swift`, thinking `None`, truncation `delete`, max_length 262144, max_model_len/top_p/top_k/repetition_penalty/model_revision `None`; stop/stop_words are present but redacted.
- `enable_thinking=None` is not explicit false. Runtime `model_revision=None` is not proof of an unpinned model: runner source pins `REV` via `snapshot_download`, and report records `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`. `eos_token_id` not extracted; stop values not compared. Adapter identities were not emitted; mapping relies on source arm order.
- R47 is retrospective inference over 20 exposed prompts / 60 outputs, not training or fresh Held-out, and contains no original-source-assistant fourth arm. It does not close R50 W2/W3/W4 and does not authorize any R50 evaluation.

R50 final state unchanged: WORLD HOLD; timepoint provenance PENDING; hidden alias closure HOLD; CPU46 verified draft-only; ROLE12 policy not approved; four-arm runtime parity not verified; admitted 0; final seal not performed; GPU/inference/training false for this R50 task.