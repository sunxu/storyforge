# StoryForge R50 — 46-case protected Held-out taskbook (2026-11-19)

**Current taskbook:** 2026-11-19  
**Scope:** R50 original 50-source inventory, Owner-excluded 4, 46-case PRESEAL candidate, source/world isolation, temporal prompt provenance, ROLE12 policy and eventual protected Held-out release gates.  
**Current disposition:** `WORLD_SEMANTIC_HOLD__W1_NO_NEW_EVIDENCE__W2_SOURCE_UNAVAILABLE_IN_SEARCHED_SOURCES__W3_NOT_TRIGGERED__CPU46_LENGTHS_DRAFT_PASS__ROLE12_POLICY_APPROVED__FOUR_ARM_RUNTIME_PARITY_NOT_VERIFIED__ORIGINAL_GOLD_COVERAGE_NOT_ESTABLISHED_OUTSIDE_EXAMINED_SOURCES__OFFICIAL_ADMITTED_0__FINAL_SEAL_NOT_PERFORMED`.

**Publication state:** This taskbook is proposed in [Draft PR #33](https://github.com/sunxu/storyforge/pull/33), branch `docs/r50-agent-handoff-20261119`; until merged, read it from that branch rather than assuming it exists on `main`.

**Execution order:** W1 is the first active task. W2 may run in parallel only as a read-only search for already-existing historical snapshots/records. W3 is conditional on new evidence from W1/W2. W4 is a separate Owner-policy/runtime-parity gate. Do not start W1–W4 as four concurrent audit workstreams. No HF Job, GPU, model inference or training is required or authorized.

> This is the current operational taskbook. It supersedes the action ordering in the 2026-10-22 snapshot `docs/r56/R56_R50_46_PROTECTED_GATE_NEXT_STEPS_20261022.md`, but does not erase that historical record. The dated 2026-11-19 audit evidence is proposed in Draft PR #32 and is not yet merged to main.

## 1. Authority and evidence precedence

Use the following order. A newer report may update status only for the scope it actually checks; it does not silently upgrade a different gate.

1. **Frozen source baseline and original intake:** `audit/r49-r50-source-intake-20261015`, including the 2026-10-16 source replay receipt and frozen source artifacts. Historical source replay reported 50/50 cases, 392/392 history references and 50/50 selected card effective intervals. Those checks do not certify actual inference-time card rendering or semantic world isolation.
2. **Owner's 50→46 selection:** original 50 remain immutable; 4 Owner-excluded; 46 PRESEAL candidates. The five R50 world groups were reported as 9/10/9/8/10 cases, with 364 historical messages and 12 trailing-User histories.
3. **2026-10-19 W17 semantic workpapers:** three pair decisions are `INSUFFICIENT_EVIDENCE`; seven later full-message gaps are `INSUFFICIENT_CONTEXT`; exact inference-effective card snapshot is not verified; the old 04→07 component and possible transitive link to W17 remain unresolved. These are existing reviews, not work to repeat without new evidence.
4. **2026-10-22/23 CPU46 and ROLE12 Owner receipts:** actual pinned Qwen tokenizer report and count-only aggregates are already recorded. CPU46 length checks are Draft-only; ROLE12 structure is reported pass, not semantic approval or four-arm runtime parity.
5. **2026-11-19 WORLD / CPU46 / ROLE12 audit reconciliation:** Owner-supplied read-only result is documented in Draft PR #32. It reports complete source bytes checked, scoped lexical/identity flags, 46/46 token lengths within Draft budget, and continued semantic/policy HOLD. See [PR #32](https://github.com/sunxu/storyforge/pull/32) and its branch file:
   `docs/evidence/V03_R50_WORLD_CPU46_ROLE12_AUDIT_20261119_CN.md`.

When a PR is still Draft/open, describe its file as proposed branch evidence, not as merged mainline policy.

## 2. Current verified/reported state

### 2.1 WORLD source inventory and scoped screen (2026-11-19 Owner read-only output)

| Field | Reported value |
|---|---:|
| Status | `FULL_SOURCE_BYTES_CHECKED__SCOPED_LEXICAL_SCREEN__SEMANTIC_HOLD` |
| Screen status | `LEXICAL_OR_IDENTITY_FLAGS_REQUIRE_AI_ADJUDICATION` |
| Source pair rows | 50 |
| Old full-source messages | 37,165 |
| R50 full-source messages | 11,627 |
| Old14 numbered-chat sources | 14 |
| Same Story ID pair count | 0 |
| Extra archive Source-ID conflicts with R50 | 0 |
| Old06_15 CRC | PASS |
| Old14 CRC | PASS |
| Exact long-message flagged pair rows | 3 |
| Sampled 120-character flagged pair rows | 3 |
| Extra archive ranks outside frozen R45 | 4 |
| New source ranks checked | 5 |
| Old source ranks checked | 10 |
| R45 source ranks checked | 9 |
| `transitive_known_old_link` | `[4,7]` (two old-source rank endpoints; not two edge objects) |
| Timepoint card-field review | PENDING |
| Hidden alias / world-component closure | HOLD |
| Final Held-out seal | NOT PERFORMED |

The three flagged pair rows are the same scoped W17 pair set already reviewed on 2026-10-19: old ranks 2, 4 and 10 against R50 rank 17. Each row has one exact long-message match and five sampled matches in the latest output. The earlier W17 pair decisions were all `INSUFFICIENT_EVIDENCE`; the prior receipt also states `reviewer_independence_or_correctness_verified_by_script=false`. Do not repeat that same review against the same evidence and call it new adjudication, and do not describe it as independently verified reviewer signoff.

**Owner rank-pair follow-up (2026-11-19):** `r45_source_ranks` contains 4 but not 7; `old_source_ranks_checked` and `old14_numbered_chat_ranks` contain both. Thus `[4,7]` is consistent with the previously recorded old 04→07 rank pair, not two link objects. The separate old→R50 `pair_aggregate` shows old rank 4 ↔ R50 rank 17 with 5 sampled 120-character matches and 1 long exact-message match (the already-reviewed W17 flag); old rank 7 ↔ R50 ranks 16–20 has zero such matches. These counts do not change the prior `INSUFFICIENT_EVIDENCE` semantic decision and do not prove world independence. The possible transitive path to W17 remains unresolved; W3 remains `NOT_TRIGGERED`.

**Interpretation boundary:** zero same-Story-ID pairs and zero extra archive Source-ID conflicts are limited identity checks. They do not prove semantic independence. The three lexical matches do not by themselves prove a shared world either. Keep semantic closure HOLD until new, source-backed provenance resolves them.

### 2.2 CPU46 tokenizer result

| Field | Reported value |
|---|---:|
| Preseal candidates | 46 |
| Recognized 46-row collection | 1 |
| All 46 token lengths verified | true |
| All 46 template/role semantics verified | false |
| Within Draft input budget | 46 |
| Over Draft input budget | 0 |
| Draft context | 16,384 |
| Draft output reserve | 1,536 |
| Derived Draft input budget | 14,848 |
| Min / median / mean | 558 / 1,362 / 1,963.7 |
| P95 nearest-rank / max | 4,265 / 8,757 |

The receipt remains `R50_HF_CPU46_TOKENIZER_SCRIPT_COMPLETED__DRAFT_NOT_ADMITTED`; it explicitly reports `full_46_token_length_and_role_checks_independently_verified=false`, `official_heldout_admitted=0`, `final_seal=false`, no GPU, no model inference and no training.

Keep both statements: the Token aggregate reports 46/46 lengths verified; the receipt does **not** claim independent full length-and-role verification. This is a Draft technical length PASS only. Do not submit another equivalent HF/CPU Tokenizer job unless a new, specifically identified defect or changed frozen input is demonstrated and the Owner authorizes it.

### 2.3 ROLE12 result

| Field | Reported value |
|---|---:|
| Historical messages | 364 |
| History roles/order preserved | 46/46 |
| Trailing-User histories | 12 |
| Consecutive User appended | 12/12 |
| Real tokenizer encoding records for those 12 | 12/12 |
| Within Draft budget | 46/46 |
| Four-arm runtime role parity verified | false |
| Trailing-User interpretation policy | PENDING OWNER DECISION |

Status: `R50_ROLE12_SOURCE_TO_DRAFT_TEMPLATE_AND_TOKEN_REPORT_STRUCTURE_PASS__NOT_SEMANTIC_APPROVAL`.

This is source-to-Draft structure evidence only. It does not approve the interpretation of User→User turns or prove Base/v0.1/v0.2/v0.3-A runtime role/template parity.

**Historical-status clarification:** the table above reflects the original 2026-11-19 audit receipt before the later explicit Owner decision. The Owner subsequently approved the two-independent-consecutive-User-turn policy; see Sections 4 and 8. This supersedes only the policy-pending flag. The 46/46 structure receipt remains Owner-reported, and actual four-arm runtime parity remains `NOT_VERIFIED`.

## 3. Existing evidence — do not repeat

The incoming agent must read these artifacts and treat them as completed historical work unless a concrete evidence-integrity defect is found:

| Existing artifact | What it already establishes | Do not repeat |
|---|---|---|
| `docs/evidence/V03_R50_REAL_SOURCE_REPLAY_20261016.json` on `audit/r49-r50-source-intake-20261015` | 50/50 source cases, 392/392 historical references, 50/50 selected card effective intervals | Do not rerun the same archive/source replay or CRC inventory |
| `docs/evidence/V03_R50_W17_AI_SEMANTIC_DECISION_SAFE_SUMMARY_20261019.json` on audit branch | Three scoped pair verdicts, all `INSUFFICIENT_EVIDENCE`; zero clear/world-link decisions | Do not repeat the same three AI pair reviews with the same dossier/evidence |
| `docs/evidence/V03_R50_W17_FULL_MESSAGE_AI_REVIEW_OWNER_RECEIPT_20261019.json` on audit branch | Seven gaps, all `INSUFFICIENT_CONTEXT`; 344 dossier entries; 75 scoped citations; no historical card timing checked | Do not repeat the same seven full-message reviews without new provenance |
| `docs/evidence/V03_R50_W17_TIMEPOINT_METADATA_OWNER_RECEIPT_20261019.json` on audit branch | Metadata timing review; actual prompt-cutoff card validity not certified; no historical content versions or moderation snapshots | Do not re-run metadata-only review and call it runtime snapshot proof |
| `docs/evidence/V03_R50_CPU46_OWNER_TOKEN_LENGTH_SAFE_AGGREGATE_20261023.md` | 46/46 Token lengths within the unapproved Draft budget | Do not rerun the same tokenizer job for the same frozen input |
| `docs/evidence/V03_R50_ROLE12_OWNER_INTAKE_SAFE_20261023.md` | 46/46 history role/order structure and 12/12 trailing User tokenizer records reported | Do not rerun the same Owner-local ROLE12 audit |
| `docs/R50_ROLE12_OWNER_LOCAL_REPLAY_CN.md` | Exact Owner-local command, pinned run key and limitations | Use as historical runbook; do not rerun absent a new identified mismatch |
| `docs/evidence/V03_R50_WORLD_CPU46_ROLE12_AUDIT_20261119_CN.md` in PR #32 branch | Latest reconciliation of the supplied 2026-11-19 output | Do not create a second copy of the same audit receipt |

Other historical context:
- `docs/evidence/V03_R50_OWNER_STORY_INDEPENDENCE_ATTESTATION_AND_R56_NEXT_GATE_20261023.md` records the Owner's attestation of intended story independence. It is not independent source proof. Do not ask the Owner to repeat the same attestation; do not use it to override current semantic HOLD.
- `docs/r56/R56_R50_46_PROTECTED_GATE_NEXT_STEPS_20261022.md` is a historical next-step snapshot. Its old suggested R45 full-history scan must be reconciled against the newer 2026-11-19 full-source inventory before any such scan is considered. Do not blindly execute it.

## 4. Remaining work — strictly sequenced

### W1 — First: complete the historical-evidence coverage crosswalk

**This is the first active task and the prerequisite for deciding whether any new semantic adjudication is warranted. Do not start W3 before W1 is complete.**

**Goal:** prove which historical evidence sets, source scopes and provenance records are already covered by the 2026-11-19 50-row inventory and which, if any, are genuinely new.

- Confirm the three flagged rows are the same old-rank 2/4/10 ↔ R50-rank-17 pairs already recorded in the W17 safe summary.
- Map the 2026-11-19 inventory against the W17 pair dossier, seven full-message gap dossier, source/archive manifests, frozen R45 scope and known transitive-link records.
- For each source/evidence family, record: artifact path and exact ref, covered scope, source/hash or version pins where available, cutoff coverage, prior review status, and whether the 2026-11-19 result adds any new message, alias, event, card version, rule version or runtime provenance.
- Reconcile `transitive_known_old_link=[4,7]` with the previously recorded old 04→07 edge; do not interpret the array length as two separate edges.
- Use existing manifests and receipts first. Do not repeat CRC checks, lexical scans or prior AI reviews against unchanged bytes/evidence.
- If the inventory does not bind a necessary source scope, identify the exact gap and why it matters. Propose only the smallest read-only check needed; do not run it without Owner authorization.
- Output: a sanitized coverage crosswalk with counts, source refs and one overall result: `NEW_EVIDENCE_PRESENT` or `NO_NEW_EVIDENCE`. No private identifiers or text.

**W1 stop condition:** if no genuinely new provenance is found, record `NO_NEW_EVIDENCE`, preserve the current HOLD, and do not manufacture another round of review.

### W2 — In parallel with W1 only: search for already-existing historical card/rule snapshots

W2 may proceed alongside W1 because it is a search/inventory of existing records, not a new audit or reconstruction. Do not broaden it into fresh data collection or runtime execution.

The 2026-10-19 timepoint receipt explicitly says actual inference-effective card validity at the case cutoff is `NOT_CERTIFIED`; the seven full-message gaps show historical card timings `NOT_CHECKED`.

Search existing, authenticated, Owner-held locations for:
- exact historical card/version snapshots effective at each relevant case cutoff;
- existing prompt-assembly/runtime records proving which card fields were visible to the model;
- long-term rule versions and applicability windows at the same cutoff;
- immutable timestamps, source/version identifiers and hashes sufficient to bind each snapshot to the corresponding frozen case and source record.

Record what locations/ref ranges were searched and what artifact types were or were not present. Metadata such as card creation/last-edit time, export-time card text, or a current card snapshot is not proof of what the model actually saw at inference time.

If the required historical snapshots/records are not present in the existing sources searched, record `SOURCE_UNAVAILABLE` / `HOLD` with the exact missing proof. Do not reconstruct or backfill historical facts from present-day cards. Do not ask for or initiate a new export until the existing-source search is reported and the Owner decides whether to authorize a targeted retrieval.

### W3 — Conditional: targeted alias/event/transitive world-component adjudication

**Do not start W3 merely because three lexical flags exist. Start only if W1 or W2 identifies genuinely new, source-backed provenance relevant to an unresolved edge.**

If that trigger exists:
- identify exactly which new artifact/version/message changes the evidence for a specific pair or graph edge;
- adjudicate only the affected pair/edge; do not reopen already-reviewed pairs whose evidence is unchanged;
- reconcile the old 04→07 edge and the two reported transitive old links using the W1 crosswalk;
- resolve or explicitly bound the possible transitive connection from the old component to R50 W17;
- distinguish shared platform/template text from character, organization, setting, event, timeline or plot continuity;
- keep every unsupported edge `INSUFFICIENT_EVIDENCE` and the overall graph `HOLD`.

If W1/W2 yields no new provenance, mark W3 `NOT_TRIGGERED`; retain the prior unresolved decisions and HOLD without repeating AI review.

The Owner's statement that intended story worlds are independent is recorded evidence of intent, not a substitute for the source graph.

### W4 — Separate ROLE12 gate: Owner policy decision, then four-arm runtime parity

W4 is independent of the W1→W2→conditional-W3 evidence sequence. It must not cause W1/W2 to pause, and it must not trigger a new tokenizer job, HF Job, GPU, model inference or training.

**Owner decision recorded on 2026-11-19: APPROVED. The binding ROLE12 contract is:**

> 12 条历史末尾的 User 消息与新追加的 User 消息，是两条独立的连续 User turn。四个模型臂均原样保留两条消息，不合并、不改写、不删除，并将其作为统一输入合同的一部分。

Record `ROLE12_POLICY = APPROVED` against contract `V03_R50_FOUR_MODEL_PLUS_ORIGINAL_GOLD_CONTRACT_20261119_CN.md`. This approval does not verify actual runtime parity and does not authorize model execution.

After the policy is decided, verify the actual Base/v0.1/v0.2/v0.3-A runtime construction against that one contract: role sequence, system/card/rule order, tokenizer/template pins, truncation, generation reserve, EOS/sampling and model-specific differences. This is a read-only configuration/code/receipt parity check; no model execution is needed or authorized. Preserve frozen source messages unchanged.

**Execution boundary for W1–W4:** no HF Job, paid tokenizer job, GPU, model inference, training, answer-key access, final seal or promotion.

### W5 — Prepare the eventual release preregistration, but do not execute it

Only after W1–W4 are resolved and Owner approves the evidence:
- freeze exact model/adapter revisions and hashes;
- freeze the identical four-arm prompt/input/runtime contract;
- predeclare generation settings, output limits, EOS behavior and failure handling;
- predeclare scoring dimensions, player-agency/forbidden-content handling, blind reviewer independence and adjudication;
- predeclare world-cluster-aware analysis and GO/NO-GO thresholds;
- specify answer-key/randomization custody and access/unblinding controls.

This is preparation only. It does not authorize private prompt sealing, inference, GPU, training, or promotion.

## 5. No-repeat ledger for the incoming agent

Before doing anything, mark each item as `ALREADY_DONE`, `NEW_EVIDENCE_REQUIRED`, `OWNER_DECISION_REQUIRED` or `NOT_AUTHORIZED`.

**Already done — do not repeat:**
- Old06_15 and Old14 archive CRC checks reported PASS.
- Full source bytes checked for the current scoped inventory.
- 50-row source-pair inventory and scoped lexical/identity screen reported.
- Three W17 pair reviews and seven full-message gap reviews already performed; all unresolved.
- CPU46 actual pinned tokenizer job and 46-length aggregate.
- ROLE12 Owner-local structure/tokenizer audit.
- 2026-11-19 reconciliation note in PR #32.

**New evidence required:**
- actual historical inference-time card/rule snapshots or proof of unavailability;
- missing alias/character/event/timeline provenance needed for graph closure;
- source coverage crosswalk if the latest inventory does not explicitly bind all previously reviewed dossiers.

**Owner decision required:**
- four-arm runtime/role parity evidence and acceptance (the consecutive-User interpretation policy is already approved);
- independent reviewer and preregistration acceptance;
- any final protected release/seal or inference authorization.

**Not authorized:**
- final Held-out admission or seal;
- any R50 model inference, paid HF Job, GPU or training;
- answer-key access, unblinding, model promotion;
- rewriting, filtering, merging, truncating or reordering frozen R50 history;
- committing private source text, per-case mappings, case IDs, answers or raw reports.

## 6. Handoff acceptance / completion criteria

The task is not complete merely because a report is written. The incoming agent must produce:
1. W1 historical evidence coverage crosswalk, completed first;
2. W2 existing-snapshot search result, run in parallel with W1, with evidence pins or explicit `SOURCE_UNAVAILABLE`;
3. W3 targeted alias/event/transitive adjudication only if W1/W2 provides a new-evidence trigger; otherwise mark `NOT_TRIGGERED` and preserve HOLD;
4. a separate explicit ROLE12 Owner decision and read-only four-arm parity status;
5. a refreshed gate matrix and next-owner-action list.

Every claim must identify its evidence tier: independently verified repository artifact, Owner-local SAFE receipt, Owner testimony, or agent inference. Never upgrade an Owner-local receipt to an independent source replay.

**Final state until all gates are independently closed and separately authorized:**
```text
WORLD_SEMANTIC_ISOLATION = HOLD
TIMEPOINT_CARD_RULE_PROVENANCE = PENDING
HIDDEN_ALIAS_WORLD_COMPONENT_CLOSURE = HOLD
CPU46_TOKEN_LENGTHS = VERIFIED_DRAFT_ONLY
ROLE12_STRUCTURE = PASS_AS_REPORTED
ROLE12_POLICY = APPROVED
FOUR_ARM_RUNTIME_ROLE_PARITY = NOT_VERIFIED
OFFICIAL_HELDOUT_ADMITTED = 0
FINAL_SEAL = NOT_PERFORMED
GPU_USED = false
MODEL_INFERENCE_RUN = false
TRAINING_RUN = false
```


## 7. Execution update — 2026-11-19 (after W1/W2)

The W1/W2 coverage crosswalk has been completed and committed on this taskbook branch:

- `docs/evidence/V03_R50_W1_W2_COVERAGE_CROSSWALK_20261119_CN.md`
- Crosswalk commit: `7040f67b79f98b78162c34c75c47983495774be0`
- Crosswalk blob (before this update): `b963d9754d01dc97d07065c6398bddbaf51250cf`

**W1 result:** `NO_NEW_EVIDENCE__EXISTING_W17_FLAGS_RECONFIRMED`. The three lexical flags are the same old-rank 2/4/10 ↔ R50-rank-17 pairs already reviewed. Owner's follow-up binds `transitive_known_old_link=[4,7]` to two old-source rank endpoints, consistent with the previously recorded 04→07 pair; it is not a count of two edge objects. The possible transitive path from that old component to W17 remains `INSUFFICIENT_EVIDENCE`. This rank clarification adds no new semantic provenance.

**W2 result:** `SOURCE_UNAVAILABLE_IN_SEARCHED_SOURCES__TIMEPOINT_CARD_RULE_RUNTIME_PROOF`. The searched GitHub source tree and available R50 Library artifact inventory contain export-time card/source material and saved checkpoint context, but no authenticated per-case inference-time card/rule snapshot or prompt-assembly receipt. Existing source-message rule references are partial provenance, not proof of the exact runtime system prompt. This does not claim exhaustive access to every Owner-held storage location.

**Downstream disposition:**
- W3 = `NOT_TRIGGERED`; do not repeat the same three pair reviews or seven full-message reviews.
- WORLD semantic isolation and timepoint card/rule provenance remain HOLD/PENDING.
- W4 remains separate. The exact consecutive-User policy was explicitly approved by the Owner on 2026-11-19; actual four-arm runtime parity remains unverified.
- No new CRC, lexical scan, tokenizer job, ROLE12 audit, HF Job, GPU, inference, training, answer-key access, or Final Seal was performed.


## 8. Execution update — 2026-11-19 (Owner policy approval and Original Gold comparison)

Owner explicitly replied **“批准”** to the exact consecutive-User contract. This supersedes earlier pending-decision language in this taskbook:

- `ROLE12_POLICY = APPROVED`
- 12 trailing historical User messages and the newly appended User remain two independent consecutive User turns.
- All four arms must preserve exact role/order/content; no merge, rewrite, or deletion.
- The policy approval does **not** establish four-arm runtime parity.

A R50-specific comparison contract was added:

- `docs/plans/V03_R50_FOUR_MODEL_PLUS_ORIGINAL_GOLD_CONTRACT_20261119_CN.md`
- Commit: `4188661a40e5f8c7f245646f8d2b0b0718e456fd`
- Blob: `7a61fa7fbd53d4d390a052fb2c4e5cab4fdda08a`

The design is **four model arms plus one historical Original Gold reference**, not five models. Original Gold is included only when the exact same current User input, full preceding history, System/Card/Rules as-of cutoff, authenticated original Assistant source reply, and source-byte hash all match. The existing R50 source schema is prompt-only and does not establish 46/46 Original Gold availability. Therefore:
- exact-match cases use a five-way denominator;
- unmatched cases remain eligible for four-model comparison;
- Gold coverage is reported separately as `N_gold / 46`;
- no similar story reply, Gold195, later-edited reply, or newly written answer may be relabeled Original Gold;
- any new human reference requires separate authorization and must be labeled `NEW_HUMAN_REFERENCE`.

The same contract specifies blind randomization, three independent reviewers, six dimensions, a separately frozen v0.3-A vs v0.2 direct pairwise comparison, case-level serious-error adjudication, and world-clustered uncertainty. It does not authorize R50 inference or scoring now.

**Current W4 disposition:** policy is approved; actual Base/v0.1/v0.2/v0.3-A runtime parity remains `NOT_VERIFIED`. The next permitted action is a read-only inspection of already-existing Owner-local runtime/load/config receipts. If no such historical records exist, record `SOURCE_UNAVAILABLE`; do not launch a model or tokenizer job to manufacture proof.

```text
ROLE12_POLICY = APPROVED
FOUR_ARM_RUNTIME_ROLE_PARITY = NOT_VERIFIED
ORIGINAL_GOLD_R50_COVERAGE = NOT_ESTABLISHED
OFFICIAL_HELDOUT_ADMITTED = 0
FINAL_SEAL = NOT_PERFORMED
GPU_USED = false
MODEL_INFERENCE_RUN = false
TRAINING_RUN = false
```


### W4 source-code inventory — 2026-11-19

The following existing repository implementations were inspected to avoid repeating prior work:

- `scripts/v02_r47_eval_runner.py`: historical three-arm Base/v0.1/v0.2 inference on the exposed R47 20-case set; not an R50 four-arm runtime receipt.
- `scripts/v03_r55_gold5_build.py`: offline packaging of already-existing R55 Base/v0.1/v0.2/v0.3-A/Original Gold responses; no R50 access and no model generation.
- `scripts/v03_r54_gpu_runner.py`: R54 training and one-candidate Adapter reload engineering workflow; not four-arm parity.
- `scripts/v03_r50_role12_owner_audit.py`: already-completed Draft structure/Tokenizer receipt; it explicitly does not verify actual four-arm runtime parity.

No R50-specific four-arm inference runner or four-arm actual-load receipt was found in the inspected GitHub source. Historical R47 generation parameters are precedent only and cannot be asserted as effective R50 parameters. W4 therefore requires already-existing Owner-local per-arm load/config/runtime records. The Owner has authorized read-only inspection, but this chat has no direct Owner Mac filesystem connector. If those historical records do not exist, record `SOURCE_UNAVAILABLE`; do not launch a model or job to manufacture evidence.


### W4 historical parameter discrepancy noted

The inspected historical runners show why old settings cannot be assumed to prove R50 parity:
- R47's Base/v0.1/v0.2 runner constructs all three inference commands from one helper and specifies `max_new_tokens=1536`, seed/data_seed 42, temperature 0, no shuffle, Transformers/BF16/BNB4.
- R54 checkpoint-16's one-sample Adapter reload smoke uses `max_new_tokens=128` and `val_dataset_sample=1`; it is an engineering reload check, not a comparable four-arm generation run.
- R55 Gold5 only packages existing responses and performs no model generation.

These historical records are useful provenance, but they do not prove the effective R50 runtime configuration. The R50 four-arm generation contract must freeze effective values before any separately authorized inference. No such inference is authorized now.


### Existing static four-arm input receipt and bounded Original Gold inventory search

The Library artifact `R50_46_DEEP_TRIAGE_REPORT_20261016.md` records a shared static Draft message-sequence SHA256 `9ad0254f740a979e9b79b458a22e61e40db4ff98fb946e0332cf172e6888565c`, covering 46 cases, 364 historical messages and 12 consecutive User→User endings. The report explicitly says this is a shared Draft message buffer only, not tokenizer input-ID proof and not actual four-arm model/runtime execution. Reuse this as historical static-input evidence; do not rerun the same static builder.

The available R50 Library directory inventory contains 106 entries, including frozen candidate/provenance, W17 review packets, CPU46 and ROLE12 artifacts. The searched R50 inventory did not reveal a dedicated Original Gold reply package. This is bounded to the searched R50 directory, not proof that no relevant historical reply exists in any other Owner-held source. Therefore `ORIGINAL_GOLD_R50_COVERAGE = NOT_ESTABLISHED`; exact-match source lookup remains required before any five-way score.

The R50-specific contract now records both limitations and the exact-match rule. No original reply text or private mappings were opened or copied into Git.


### Original Gold source availability update — 2026-11-19

See SAFE receipt `docs/evidence/V03_R50_ORIGINAL_GOLD_SOURCE_AVAILABILITY_20261119_CN.md` (commit `0c0bec3e4dc495ce35e49c2e59b446c637a78c0c`). Owner-provided local output verifies both 14-chat archive copies are byte-identical and match the expected size/SHA256/ZIP CRC; the 06–15 archive also matches its expected size/SHA256/ZIP CRC. These are Owner-reported checks, not independent agent access to the Mac files. Do not repeat them on unchanged bytes.

The pinned 2026-10-16 source replay compared all 50 new User inputs with User messages in the five pinned R50 source transcripts and reported `source_input_normalized_verbatim_reuses=0`. Therefore no protected 46 case has an exact current-User-input match in those five transcripts (`0/46` within that pinned source scope). This does not prove 0/46 across all Owner-held sources: the 14-chat and 06–15 archives have not been searched for exact full-history matches. Overall `ORIGINAL_GOLD_R50_COVERAGE = NOT_ESTABLISHED`. Any further lookup must compare exact current User input and complete preceding history/cutoff context and emit aggregate counts only. Do not rerun the five-world replay, CRC, W17 lexical scan or prior AI reviews.


### Supplementary archive scope reconciliation — 2026-11-19

See SAFE receipt `docs/evidence/V03_R50_ORIGINAL_GOLD_SOURCE_AVAILABILITY_20261119_CN.md` (follow-up commit `fea7d2e1b15375b631d24ad650b545ec7174d889`). The Owner-run scan parsed 14 actual conversations in the 14-chat archive (14 AppleDouble metadata entries were identified and excluded) and 1,010 conversations in the nested 06–15 archive. Neither yielded an exact 32-message history sequence or positive provenance Message-ID match for the protected 46. These archives are outside the five pinned R50 source worlds 16–20; do not repeat these scans without a new independent provenance lead.

The authoritative 2026-10-16 replay remains 392/392 history references, 50/50 contiguous history/cutoff checks, and zero normalized verbatim reuse of the 50 new User inputs in the five pinned source transcripts. Therefore pinned-source Original Gold eligibility is 0/46. Overall Owner-wide coverage remains `NOT_ESTABLISHED` outside examined sources. Cases without Gold use the four-model comparison; a historical continuation after cutoff is not an answer to the appended current User input.


### W4 historical implementation search update — 2026-11-19

Read-only GitHub inspection located the historical R48/R55 comparison pipeline:

- R48 is four answers total: Original Gold + Base/v0.1/v0.2, built from already-completed R47 outputs on 20 exposed prompts.
- R55 is five answers total: Original Gold + Base/v0.1/v0.2/v0.3-A, with exact-source validators, frozen output/report hashes, anonymous five-way sheets, and a separately randomized v0.3-A vs v0.2 direct pairwise sheet. Its scope is the same 20 exposed prompts across two worlds; the 2026-10-23 preparation receipt says real Owner-local preflight was still pending.

This closes the **design/implementation precedent** question for the five-answer review package. It does not close R50 W4 runtime parity: R47/R55 are old exposed prompts, not the protected 46, and no R50-specific four-arm load/runtime receipt was found. Reuse the R55 design/validators only as a reference; do not run its build/preflight against R50 or reuse exposed outputs as R50 answers. W4 remains NOT_VERIFIED pending existing R50 per-arm runtime/load evidence.


### R55 Gold5 v2 historical outcome located — 2026-11-19

The later Owner-unblind SAFE aggregate at docs/evidence/V03_R55_GOLD5_V2_OWNER_UNBLIND_DECISION_20261023.md supersedes the earlier 2026-10-23 *builder-preparation-only* receipt for the status of the subsequent v2 development review. It reports 20 exposed prompts / two worlds, three reviewers and 3,960 Pair/Four/Five ratings. Pair v0.3-A vs v0.2 was 10:10 and v0.3-A was lower on all six dimensions. Five-way means were Original Gold 3.500, v0.2 3.461, v0.3-A 3.197. The Owner decision retained v0.2 and kept R54 checkpoint-16 NO-GO for R50. These are Owner-pasted aggregate results; reviewer independence was not technically certified and hard-event adjudication remained pending. This is historical development evidence only, not R50 or fresh Held-out evidence.


### Owner-local follow-up correction — W1 and R55 final evidence

The latest targeted inventory reports `transitive_known_old_link` as a list of two integers. Do **not** call this two edges: the prior `LINK_COUNT` was only list length. It may encode one endpoint pair or compact references; inspect the values and parent schema before interpreting it. The 04→07 edge remains unresolved.

The local R55 inventory also contains the subsequent arbitration/second-audit/third-audit/final-evidence artifacts. The documented pipeline covers 76 flagged candidates × 2 categories (152 slots), with P0=65 and P1=87; third audit covers 46 candidates / 92 slots, including 59 original disputes/first-HOLD categories. The third-audit receipt says no automatic majority adjudication and reviewer independence not technically verified. Final-evidence format/quote validation is not semantic certification. Local file existence alone does not establish PASS: inspect the safe count-only outputs for arbitration, second audit, third audit, priority final validation, and all-152 final validation. Never upload private dockets, story text, candidate replies, mappings, or private decision JSON.

W4 remains HOLD: the existing R50 Role12 count-only evidence says actual four-model runtime interpretation/role parity=false. Its `trailing_user_interpretation_policy_approved=false` field predates the Owner's explicit 2026-11-19 approval and is superseded for policy status only. CPU tokenizer draft fit is not deployed four-arm parity. No R50 inference, seal, or admission follows from this inventory.


## R55 safe-receipt update — 2026-11-19

Owner supplied all five safe count-only receipts. The first arbitration receipt validates 76 flagged candidates × 2 categories (syntax/exact quotations only; reviewer independence unverified; no R50). The second audit validates 68 candidates / 136 category decisions; 44 categories were mutually CONFIRMED by the first two arbiters and 59 were disagreement or first-HOLD categories requiring third review. The third audit validates 46 candidates / 92 category decisions, including the 59 original unresolved categories; it explicitly does not perform automatic final adjudication and does not technically verify reviewer independence.

The Owner's final evidence safe receipts now show:
- Priority P0: 65 category judgments; 38 CONFIRMED, 4 HOLD_INSUFFICIENT_EVIDENCE, 23 REJECTED; 87 were not yet included in that staged validation.
- All 152: 79 CONFIRMED, 4 HOLD_INSUFFICIENT_EVIDENCE, 69 REJECTED; `not_reviewed_in_this_validation=0`; status `R55_GOLD5_FINAL_EVIDENCE_ALL_152_FORMAT_VERIFIED__NOT_SEMANTIC_CERTIFIED__NO_R50`.
- P1 derived by subtracting the P0 receipt from the all-152 receipt: 41 CONFIRMED, 0 HOLD, 46 REJECTED across 87 slots. This is arithmetic over the two count-only receipts, not a separately emitted P1 report.

This closes the **mechanical completion/format-and-quotation validation** of all 152 originally flagged category slots, but it does NOT establish independent reviewer blinding, semantic correctness, or an unbiased model-wide failure rate. Four final Owner decisions remain HOLD for insufficient evidence. R55 remains development-only; R50 was not accessed, no GPU/training started, and no model promoted. Do not spend the protected R50 holdout based solely on these receipts.

W1 rank-pair follow-up: Owner supplied `transitive_known_old_link=[4,7]`; both values are old-source ranks, rank 4 is in frozen R45 and rank 7 is outside R45 but in the checked old-source/Old14 scope. This is consistent with the previously recorded 04→07 rank pair, not two edge objects. The separate old↔R50 rows show the already-reviewed old rank 4 ↔ R50 rank 17 flag (5 sampled matches, 1 long exact match) and zero reported matches for old rank 7 against R50 ranks 16–20. No new semantic evidence; the possible transitive path to W17 remains `INSUFFICIENT_EVIDENCE` and W3 `NOT_TRIGGERED`.


## 2026-11-19 follow-up — supplementary Gold lookup and CI

Owner's corrected read-only archive parser excluded the 14 AppleDouble metadata entries, parsed 14 actual 14-chat conversations (62,583 messages), and recursively parsed 1,010 conversations (71,884 messages) from the 06–15 archive. The exact-history scan reported no full 32-message history matches in either supplementary archive; the Message-ID-first diagnostic had no positive matches. These unchanged archives must not be scanned again absent a new provenance lead. Original Gold remains `NOT_ESTABLISHED_OUTSIDE_EXAMINED_SOURCES`; the five pinned R50 source worlds remain 0/46 eligible.

PR #33 CI at head `e95da034bde9d064082dcfa32908ebd1290ec6b5` completed with repository-wide Ruff failure (202 findings); test and evidence-integrity steps were skipped. This is the known unrelated repository-wide lint debt. Do not expand this documentation task into whole-repository Ruff cleanup.


## 2026-11-19 W4 partial runtime evidence reconciliation

A read-only cross-reference of the R47/R55 execution code and already-existing SAFE reports found partial runtime precedent, but **does not close four-arm parity**:

| Arm / evidence | Existing evidence | What it establishes | What remains unproven for R50 |
|---|---|---|---|
| Base / v0.1 / v0.2 — R47 | `scripts/v02_r47_eval_runner.py` on `main` (blob `a2fa43f65b7b31631976cab1ac84b2b183b5f352`); R47 run `r47-20261014T091647Z-637890` | One shared `swift infer` path; pinned Qwen revision; Transformers backend; BF16 / BNB 4-bit; `max_new_tokens=1536`, `seed=42`, `data_seed=42`, `temperature=0`, no validation shuffle; per-adapter weight SHA guards | R47 used exposed v0.1 test prompts, not the R50 46-case prompt assembly. Script does not explicitly pin/report R50 chat-template hash, `enable_thinking`, truncation, EOS/stop policy, or effective per-case input IDs |
| v0.3-A — R55 | Owner-held `r55/inference-results/r55-dev-20261022T023436Z-188604/R55_R54_INFERENCE_REPORT_PRIVATE.json`; Library SAFE report records 20 rows, Qwen revision `1d4bf0f...`, R54 checkpoint-16 adapter SHA `121ec8...`, `ms-swift=4.5.3`, `transformers=5.16.1`, `bitsandbytes=0.50.2`, and the same seed/temperature/max-new-token values | The R54 adapter was used for a completed 20-row exposed-development inference; no training, R50 access or promotion | The SAFE report does not expose effective backend/template, role sequence, `enable_thinking`, truncation, EOS/stop, or R50 input IDs. The local R55 runner/runtime log exist but have not been inspected for those allowlisted fields in this pass |
| R50 common draft | `R50_ROLE12_OWNER_SAFE_AUDIT.json` | 46/46 history role/order structures preserved; 12/12 trailing-User sequences encoded; pinned Transformers tokenizer/template hashes; 46/46 within Draft budget | The receipt itself says `actual_four_arm_runtime_role_parity_verified=false`; it is not proof of the actual ms-swift serving path |
| Cross-backend warning | R53 CPU40 report-only receipt | In that separate R53 data audit, `transformers_ms_swift_input_same=false` was reported on 31 Train + 9 Validation rows | R53 is not R50; this is a reason to verify the exact R50 runtime path, not evidence that R50 inputs differ |

**W4 current result:** `PARTIAL_HISTORICAL_RUNTIME_PRECEDENT__FOUR_ARM_R50_PARITY_NOT_VERIFIED`.

**Smallest next read-only Owner action:** inspect only the existing local R55 runner, R55 contract/report/runtime log and R47 report at the paths recorded in the R50 handoff. Emit hashes plus allowlisted effective settings/flags (backend, model/adapter identity, tokenizer/template, thinking, truncation, max context/output reserve, EOS/stop, sampling, and whether two consecutive User roles survive). Do not print prompts, responses, case IDs, private mappings, answer keys or full logs. Do not rerun R47/R55, start a tokenizer/HF Job, load a model, or execute inference. If a setting is not captured by existing artifacts, report `NOT_RECORDED`; do not infer it from code defaults.


## 2026-11-19 Owner-local R47/R55 Runner and report hashes — W4 update

The Owner ran a read-only allowlisted inventory against the exact historical local files. All listed file hashes below are SHA256 of the local file bytes (not Git blob IDs):

| Artifact | SHA256 | Finding |
|---|---|---|
| R47 Runner | `97270d6146a3a8ae8f1a2bf66b409bf26aba04735229e9b340f535435bbf6bae` | Core CLI flags extracted |
| R47 report | `9b5066004234e4140b9a6025843f836e2be22e8a3af61f8ab1a9340b9f93e253` | Base/v0.1/v0.2 complete; 20 rows; model revision and adapter/result hashes present |
| R55 Runner | `f318bd318d818e4ccd1f9e2ec5a81252291c5e13d5084afb241ae99d89cbceb6` | Core CLI flags extracted |
| R55 contract | `1d500f48360f46e2d8ff2c9ab89ba4620a67af3e95761c8cda64817d7e440b64` | Pre-run state `ONE_PAID_GPU_INFERENCE_AUTHORIZED_NOT_STARTED`; later superseded by completion report/intake |
| R55 report | `924404daa12ed5886a879e4445b7995350228f559995f646d480859f76c4fd64` | 20-row generation complete; R54 checkpoint-16 adapter SHA `121ec8...`; no promotion / no R50 |
| R55 intake | `a8569b96dc8a655dbc79046b0b24128cb459d8c9c1323f9806aecaa6fcfdd158` | Owner intake PASS for exposed 20-row development generation |
| R55 runtime log | `f83f877441c38fbb1ef705a8b2e6acd0a4603bd14fcdd280741fe9e905cdfee3` | 243,541 bytes; first extraction searched only literal `COMMAND:` markers and found 0; this is not proof that the log lacks runtime details |

Both local Runner sources returned the same allowlisted values: `use_hf=true`, `infer_backend=transformers`, `torch_dtype=bfloat16`, `quant_method=bnb`, `quant_bits=4`, `bnb_4bit_compute_dtype=bfloat16`, `max_new_tokens=1536`, `seed=42`, `data_seed=42`, `temperature=0`, `val_dataset_shuffle=false`. Neither source mentions `enable_thinking`; neither source-flag extraction surfaced explicit template, truncation, EOS/stop, context-length, top_p/top_k or repetition-penalty flags.

R47 report records completed arms Base/v0.1/v0.2 on the same pinned Qwen revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`, with v0.1/v0.2 adapter hashes and per-arm result hashes. R55 report records the same Qwen revision and its actual R54 adapter hash, 20 rows, dependency versions, and the same visible generation values. R55's contract is a pre-run authorization artifact; its `NOT_STARTED` status is superseded chronologically by the later generation report and Owner intake PASS, not a contradiction.

**W4 revised result:** `PARTIAL_HISTORICAL_RUNNER_CONFIG_MATCH__R50_RUNTIME_PARITY_NOT_VERIFIED`. The Runner sources prove shared explicit CLI settings in their historical code, not all effective runtime defaults or R50 46-case execution. `enable_thinking_mentioned=false` means only that the inspected source contains no such explicit mention; it does not establish the effective default. The first runtime-log extraction found no literal `COMMAND:` marker and therefore did not extract command-line arguments. A second safe parser must scan the log by field names and report only allowlisted values/presence/line numbers, never raw log lines.

**Next action:** inspect the existing R55 runtime log and both Runner source files for effective `template`, thinking, truncation, context, EOS/stop and sampling values using a field-oriented read-only parser. Also verify whether the logs contain a safe indication of the two-consecutive-User role sequence; if not recorded, state `NOT_RECORDED`. No model, tokenizer, GPU or HF job may be started to fill missing evidence.


Latest PR #33 CI after Owner-local Runner evidence update: head `1c5aba1b6601ad372df00c98169073ed82f2aed8` completed failed at `ruff check .` with 202 findings; tests and evidence-integrity stages were skipped. This is the same repository-wide lint blocker, not a newly isolated R50 failure. Keep the documentation-only scope; do not broaden to whole-repository Ruff cleanup.


## 2026-11-19 R55 effective runtime-log extraction — W4 update 2

Owner supplied a second SAFE field-oriented scan of the existing 243,541-byte R55 runtime log. Its SHA256 remains `f83f877441c38fbb1ef705a8b2e6acd0a4603bd14fcdd280741fe9e905cdfee3`. No raw log lines, prompts, responses, case IDs or mappings were emitted.

**R55 runtime-log fields observed:**

| Field | Observed value / status | Evidence scope |
|---|---|---|
| `infer_backend` | `transformers` | runtime log lines 399, 410 |
| `use_hf` | true | lines 399, 410 |
| `torch_dtype` | `bfloat16` / `torch.bfloat16` | lines 399, 410 |
| `quant_method` | `bitsandbytes` / `bnb` | lines 399, 410, 440 |
| `quant_bits` | 4 | lines 399, 410 |
| `bnb_4bit_compute_dtype` | `bfloat16` / `torch.bfloat16` | lines 399, 410, 426 |
| `template` | `qwen3_8` | line 410 |
| `template_backend` | `swift` | line 410 |
| `enable_thinking` | `None` | line 410; effective default/behavior not established |
| `truncation_strategy` | `delete` | line 410 |
| `max_length` | 262144 | lines 410, 498 |
| `max_model_len` | `None` | line 410; not a proven effective context limit |
| `max_new_tokens` | 1536 | lines 399, 410 |
| `temperature` | 0 / 0.0 | lines 399, 410, 4502 |
| `seed` | 42 in runtime invocation/config records; `None` in a separate record at line 4502 | scope not reconciled; do not flatten into one effective value |
| `data_seed` | 42 | lines 399, 410 |
| `val_dataset_shuffle` | false | lines 399, 410 |
| `stop_words` | present; value withheld | line 410 |
| `stop` | present; value withheld | line 4502 |
| `top_p`, `top_k`, `repetition_penalty` | `None` in the separate record at line 4502 | scope/default behavior not further established |
| EOS token ID | no record found by this scan | `NOT_RECORDED` in searched log fields |

The log contains one `messages` marker at line 4512, but this is not evidence that the two-consecutive-User sequence survived serialization or reached the model. No R50 case-level role/input-ID evidence was found in this scan.

The R55 Runner source and R47 Runner source still show matching explicit core CLI settings, but the R47 Runner scan only found a non-scalar `revision` expression at line 87; the R47 SAFE report separately records the pinned Qwen revision. No R47 effective runtime log was supplied in this pass. Therefore the R55 template/truncation settings must not be projected onto R47, and neither R47 nor R55 historical exposed prompts establish R50 46-case parity.

**W4 result updated:** `PARTIAL_R55_EFFECTIVE_RUNTIME_FIELDS_FOUND__FOUR_ARM_R50_ROLE_PARITY_NOT_VERIFIED`.

**Open W4 evidence gaps:** (1) identify the scope of the line-4502 GenerationConfig seed/stop/sampling record relative to the invocation seed 42; (2) establish the effective interpretation of `enable_thinking=None`; (3) obtain the corresponding existing R47 effective template/truncation/stop record if one exists; (4) determine whether any existing runtime receipt records preservation of the two consecutive User roles and per-case input IDs. Missing historical fields remain `NOT_RECORDED`; do not run a model, tokenizer, GPU or HF job to create evidence. No new R50 execution is authorized.


Latest PR #33 CI after the R55 effective-runtime evidence update: head `cc9f68aaddc97442ff149cffa5f17f3729b78024` completed failed at repository-wide `ruff check .` with 202 findings; Tests and evidence-integrity stages were skipped. This is the known repository-wide lint blocker, not a new R50-specific failure. Keep this PR documentation-only.


## 2026-11-19 R47 runtime-log filename search result

Owner searched the known R47 run directory `~/.local/share/storyforge/r47/r47-20261014T091647Z-637890/` recursively for `*.log`, `*runtime*`, `*launch*`, and `*command*`; result: `MATCHED_FILES: 0`. This is a bounded filename-search result only. It does not invalidate the completed R47 three-arm inference or its existing report/results, and it does not prove no runtime metadata exists inside JSON reports or remote job records. Existing local evidence still includes `R47_PRIVATE_RUN_REPORT.json`, `R47_LOCAL_INTEGRITY_PASS.json`, `coordinator/private/R47_AUDIT_SUMMARY.json`, and Base/v0.1/v0.2 result JSONL files. Next smallest action: read-only allowlisted field scan of those existing JSON reports for runtime/template/truncation/stop/sampling fields, emitting only key paths and safe values; do not print prompts, responses, IDs or mappings. If absent, mark `NOT_RECORDED` / `SOURCE_UNAVAILABLE`; do not rerun R47 or launch any GPU/model/tokenizer job.

## 2026-11-19 R47 execution.log recovery lead — source verified

A follow-up GitHub source inspection resolves the meaning of the earlier local MATCHED_FILES: 0 more precisely:

- scripts/v02_r47_eval_runner.py (main blob SHA a2fa43f65b7b31631976cab1ac84b2b183b5f352) creates log = out / execution.log and writes each executed command prefixed by COMMAND: plus merged stdout/stderr to that file (source lines 18–26, 65).
- The same Runner stores the run under evaluation-runs/v02-r47/<RUN_KEY>/ (line 59).
- scripts/v02_r47_collect_git.sh (main blob SHA 20150d94fd460d8551838a7d7da4cae8137d2ff1) copies the report, result JSONLs and blind-review/private package files, but does not copy execution.log (lines 18–32).
- Therefore the local search result is explained by a collection-script omission; it does not establish that the remote log is absent. Remote existence still needs to be checked.
- There are two relevant historical R47 run keys: resumed three-arm run r47-20261014T091647Z-637890 (Base was reused from the earlier run) and original Base run r47-20261014T082109Z-820409. The resumed run's execution log can evidence v0.1/v0.2 inference command/runtime details; the original run's log, if retained, is needed for Base inference details.

Smallest next read-only check: using the already authenticated HF CLI, fetch only execution.log from those two exact existing run prefixes into a private temporary directory. Do not fetch the answer key, response JSONLs, prompt files, or any other private artifact. If one path is missing, record SOURCE_UNAVAILABLE for that run; do not rerun. Parse the logs locally with a field allowlist and emit only safe parameter values, booleans and line numbers. Never paste raw logs. This is evidence retrieval only; no GPU, model, tokenizer, database write, answer access or inference.
## 2026-11-19 R47 historical log objects recovered

Owner reports successful read-only download of both exact existing HF Bucket objects:

| Run | Local private filename | Bytes | SHA256 |
|---|---|---:|---|
| Original Base run `r47-20261014T082109Z-820409` | `R47_BASE_execution.log` | 84,617 | `34d3e33ca1888dbc1c61cf65c0f2619ebf41bae626deea131564db8e6a927399` |
| Resumed three-arm run `r47-20261014T091647Z-637890` | `R47_RESUMED_execution.log` | 450,504 | `18b077671b38404ff4821c4d9fb0342b3cb9430fc5d5565c9efc1586a4c3ab7c` |

Status: `SOURCE_RECOVERED` for both remote log objects; hashes/byte counts are Owner-reported local verification, not independently rehashed in this review. Runtime fields have not yet been parsed. The next step is a local allowlisted parser that emits only safe runtime field values and line numbers; raw logs remain private and must not be pasted or committed. For the resumed run, Base was reused, so the log should be used for v0.1/v0.2 and not treated as Base inference evidence. The earlier Base run log is the Base runtime source.
## 2026-11-19 R47 three-arm runtime evidence recovered and parsed (SAFE aggregate)

Owner supplied the output of a local allowlisted parser over the two recovered private `execution.log` files. No raw log, prompt, response, case identifier or private mapping was uploaded.

**File identity (Owner-reported and parser-verified locally):**
- Original Base log: 84,617 bytes; SHA256 `34d3e33ca1888dbc1c61cf65c0f2619ebf41bae626deea131564db8e6a927399`; 1,183 lines.
- Resumed log: 450,504 bytes; SHA256 `18b077671b38404ff4821c4d9fb0342b3cb9430fc5d5565c9efc1586a4c3ab7c`; 8,676 lines.

**Arm mapping:**
- Base: original run, inference command at line 395, no `--adapters`.
- Resumed run: inference commands at lines 395 and 4537, both with `--adapters`.
- Runner source `scripts/v02_r47_eval_runner.py` (main blob SHA `a2fa43f65b7b31631976cab1ac84b2b183b5f352`) iterates `(base,None)`, `(v01,V01)`, `(v02,V02)` in that order; `infer()` adds `--adapters` when adapter is non-null; the resumed run reuses the earlier Base output. Thus resumed line 395 maps to v0.1 and line 4537 maps to v0.2. This is a source+log mapping; adapter path/value was not emitted by the safe parser.

**Command-level settings matching across Base/v0.1/v0.2:** `use_hf=true`; `infer_backend=transformers`; `torch_dtype=bfloat16`; `quant_method=bnb`; `quant_bits=4`; `bnb_4bit_compute_dtype=bfloat16`; `max_new_tokens=1536`; `seed=42`; `data_seed=42`; `temperature=0`; `val_dataset_shuffle=false`.

**Runtime summary fields matching across all three commands:** `template=qwen3_8`; `template_backend=swift`; `enable_thinking=None`; `truncation_strategy=delete`; `max_length=262144`; `max_model_len=None`; `top_p=None`; `top_k=None`; `repetition_penalty=None`; `model_revision=None`; `stop` and `stop_words` present but values intentionally redacted.

**Interpretation limits:** `enable_thinking=None` is not proof of explicit `false`; `model_revision=None` in the runtime summary does not mean the model was unpinned. The Runner source calls `snapshot_download(repo_id=MODEL, revision=REV)` and the R47 report records revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`; the exact revision is therefore supported by source+report, not by the runtime summary field. `eos_token_id` was not extracted, so its effective value is unverified. Stop token contents remain unreviewed. The safe output did not disclose adapter paths/identities; arm order is mapped from Runner source.

**Scope:** R47 was a 20-prompt, 60-response retrospective GPU inference comparison (Base/v0.1/v0.2), not training and not a fresh independent Held-out evaluation. It did not include the original source assistant reply as a fourth arm. Its exposed prompts cannot satisfy R50's protected 46-case evaluation or establish independent generalization. Do not reuse R47 as R50 evidence or launch another R47 job.

**R50 gate effect:** none. This R47 evidence does not establish R50 W2 timepoint card/rule provenance, W3 world/alias closure or four-arm runtime role parity. The ROLE12 policy is now `APPROVED`; actual four-arm runtime role parity remains unverified. R50 remains HOLD; no final seal, inference, GPU, training or promotion.
## 9. Current progress after ROLE12 approval and R47 runtime-log recovery — 2026-11-19

### Completed since the initial handoff

- Owner explicitly approved `TWO_INDEPENDENT_USER_TURNS`: the 12 trailing historical User messages and the appended User message remain two separate consecutive User turns. Apply to Base/v0.1/v0.2/v0.3-A; preserve role sequence and original order; do not merge, rewrite, delete or insert Assistant messages. The policy contract is `docs/plans/V03_R50_FOUR_MODEL_PLUS_ORIGINAL_GOLD_CONTRACT_20261119_CN.md`.
- W1/W2 crosswalk is already recorded at `docs/evidence/V03_R50_W1_W2_COVERAGE_CROSSWALK_20261119_CN.md`: W1 `NO_NEW_EVIDENCE__EXISTING_W17_FLAGS_RECONFIRMED`; W2 `SOURCE_UNAVAILABLE_IN_SEARCHED_SOURCES__TIMEPOINT_CARD_RULE_RUNTIME_PROOF`; W3 `NOT_TRIGGERED`.
- Both R47 historical execution logs were recovered from the exact existing HF Bucket paths and safely parsed locally. The new receipt is `docs/evidence/V03_R50_W4_HISTORICAL_RUNTIME_EVIDENCE_SAFE_20261119_CN.md` (commit `47e01a58448cb859f401a0ce16a7cd3bd698831d`).
- R47 Base/v0.1/v0.2 logs show matching listed command/runtime fields on the old exposed 20-prompt comparison. R55's existing log provides partial v0.3-A-side historical runtime fields. These historical development runs do not prove R50's actual four-arm serialized input, load configuration or runtime parity.
- Original Gold lookup is bounded: no exact 32-message history sequence or positive provenance Message-ID match in the examined 14-chat and 06–15 archives; pinned five R50 source transcripts provide 0/46 same-current-User exact candidates. Overall `ORIGINAL_GOLD_R50_COVERAGE = NOT_ESTABLISHED_OUTSIDE_EXAMINED_SOURCES`; retain four-model comparison for cases without exact Gold.

### Current W4 blockers

1. No R50-specific four-arm inference runner or actual four-arm load/runtime receipt was found in the inspected GitHub source. Owner-local existing receipts remain to be inventoried.
2. Static Draft message-sequence SHA256 `9ad0254f740a979e9b79b458a22e61e40db4ff98fb946e0332cf172e6888565c` is not a runtime serialized-request or tokenizer input-ID receipt; it does not prove the two consecutive User roles reached each arm unchanged.
3. W2 still lacks authenticated per-case cutoff-time System/Card/Long-term Rules snapshots and prompt-assembly receipts. This blocks proof of exact shared context/order across arms.
4. Historical R47/R55 logs show `truncation_strategy=delete`, `enable_thinking=None`, and stop/stop_words presence; `enable_thinking=None` is not explicit false, stop values are redacted, and EOS was not recorded. R55 also has an unresolved `seed=42` invocation vs `seed=None` GenerationConfig-like record. These are historical settings, not R50 effective settings.
5. R50-specific effective tokenizer/template pins, no-truncation behavior, generation reserve, EOS/stop and sampling parity across all four arms remain unverified.

### Smallest next action

Run a **read-only Owner-local inventory** of already-existing R50 runtime/load/config/prompt-assembly receipts only. Return sanitized filenames, byte counts, SHA256, per-arm record counts and allowlisted field presence/values. Search for historical artifacts only; do not create a model load, tokenizer job, HF job, GPU run, inference or training. If no R50-specific four-arm receipt exists, record `SOURCE_UNAVAILABLE` and keep W4 HOLD.

### Refreshed current disposition

```text
W1_CROSSWALK = NO_NEW_EVIDENCE__EXISTING_W17_FLAGS_RECONFIRMED
W2_TIMEPOINT_CARD_RULE_RUNTIME = SOURCE_UNAVAILABLE_IN_SEARCHED_SOURCES
W3 = NOT_TRIGGERED
WORLD_SEMANTIC_ISOLATION = HOLD
TIMEPOINT_CARD_RULE_PROVENANCE = PENDING
HIDDEN_ALIAS_WORLD_COMPONENT_CLOSURE = HOLD
CPU46_TOKEN_LENGTHS = VERIFIED_DRAFT_ONLY
ROLE12_STRUCTURE = PASS_AS_REPORTED
ROLE12_POLICY = APPROVED
FOUR_ARM_RUNTIME_ROLE_PARITY = NOT_VERIFIED
ORIGINAL_GOLD_R50_COVERAGE = NOT_ESTABLISHED_OUTSIDE_EXAMINED_SOURCES
OFFICIAL_HELDOUT_ADMITTED = 0
FINAL_SEAL = NOT_PERFORMED
GPU_USED_FOR_R50_AUDIT = false
R50_MODEL_INFERENCE_RUN = false
R50_TRAINING_RUN = false
```

R47/R55 historical GPU inference and R54 training were earlier development activities. They do not mean the current R50 audit used GPU or performed R50 inference/training.