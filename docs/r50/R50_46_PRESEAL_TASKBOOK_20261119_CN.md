# StoryForge R50 — 46-case protected Held-out taskbook (2026-11-19)

**Current taskbook:** 2026-11-19  
**Scope:** R50 original 50-source inventory, Owner-excluded 4, 46-case PRESEAL candidate, source/world isolation, temporal prompt provenance, ROLE12 policy and eventual protected Held-out release gates.  
**Current disposition:** `WORLD_SEMANTIC_HOLD__CPU46_LENGTHS_DRAFT_PASS__ROLE12_POLICY_HOLD__OFFICIAL_ADMITTED_0__FINAL_SEAL_NOT_PERFORMED`.

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
| Transitive known old links | 2 |
| Timepoint card-field review | PENDING |
| Hidden alias / world-component closure | HOLD |
| Final Held-out seal | NOT PERFORMED |

The three flagged pair rows are the same scoped W17 pair set already reviewed on 2026-10-19: old ranks 2, 4 and 10 against R50 rank 17. Each row has one exact long-message match and five sampled matches in the latest output. The earlier W17 pair decisions were all `INSUFFICIENT_EVIDENCE`; the prior receipt also states `reviewer_independence_or_correctness_verified_by_script=false`. Do not repeat that same review against the same evidence and call it new adjudication, and do not describe it as independently verified reviewer signoff.

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
- Reconcile the old 04→07 confirmed edge with the two transitive known old links reported in the latest inventory; do not assume these are three distinct edges.
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

**The only pending ROLE12 interpretation decision for the Owner is whether to approve this exact contract:**

> The 12 historical trailing User messages and the newly appended User messages are two independent consecutive User turns. All four model arms preserve both messages exactly as they are, without merging, rewriting or deleting either message, and treat this structure as part of the common input contract.

Until the Owner explicitly approves or rejects this wording, keep `ROLE12_POLICY = PENDING_OWNER_DECISION`. Do not infer approval from silence or from the existence of this taskbook. If approved, record the Owner's explicit decision and contract version; if rejected or amended, record the exact alternative before changing any runtime contract.

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
- explicit Owner decision on the exact consecutive-User interpretation contract (pending until stated);
- approval of the four-arm runtime/role contract after policy wording is fixed;
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
ROLE12_POLICY = PENDING_OWNER_DECISION
FOUR_ARM_RUNTIME_ROLE_PARITY = NOT_VERIFIED
OFFICIAL_HELDOUT_ADMITTED = 0
FINAL_SEAL = NOT_PERFORMED
GPU_USED = false
MODEL_INFERENCE_RUN = false
TRAINING_RUN = false
```
