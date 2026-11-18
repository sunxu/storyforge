# StoryForge R50 — 46-case protected Held-out taskbook (2026-11-19)

**Current taskbook:** 2026-11-19  
**Scope:** R50 original 50-source inventory, Owner-excluded 4, 46-case PRESEAL candidate, source/world isolation, temporal prompt provenance, ROLE12 policy and eventual protected Held-out release gates.  
**Current disposition:**

**Publication state:** This taskbook is proposed in [Draft PR #33](https://github.com/sunxu/storyforge/pull/33), branch `docs/r50-agent-handoff-20261119`; until merged, read it from that branch rather than assuming it exists on `main`.
 `WORLD_SEMANTIC_HOLD__CPU46_LENGTHS_DRAFT_PASS__ROLE12_POLICY_HOLD__OFFICIAL_ADMITTED_0__FINAL_SEAL_NOT_PERFORMED`.

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
| Trailing-User interpretation policy approved | false |

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

## 4. Remaining work — execute in this order

### W1 — Reconcile the 2026-11-19 source inventory against existing W17 evidence

**Goal:** prove whether the latest 50-row source-pair inventory fully covers the earlier W17 pair dossier and the known transitive links.

- Confirm the three flagged rows are the same old-rank 2/4/10 ↔ R50-rank-17 pairs already recorded in the W17 safe summary.
- Confirm the 2026-11-19 source inventory's source scope, archive membership, byte pins, cutoff coverage and transitive-link accounting. Use existing manifests/receipts first.
- Establish whether the 2026-11-19 output supplies any genuinely new message, alias, event, card-version or runtime provenance beyond the 2026-10-19 W17 dossiers.
- Do not repeat CRC checks or lexical scans if the exact bytes and scope are already pinned. If a scope difference exists, document the precise uncovered source set and why it matters before proposing a new check.
- Output: a sanitized coverage crosswalk with counts, source references and `NEW_EVIDENCE_PRESENT` or `NO_NEW_EVIDENCE`. No private identifiers or text.

### W2 — Close timepoint card/rule provenance (highest-value evidence gap)

The 2026-10-19 timepoint receipt explicitly says actual inference-effective card validity at the case cutoff is `NOT_CERTIFIED`; the seven full-message gaps show historical card timings `NOT_CHECKED`.

Seek existing, authenticated, Owner-held evidence first:
- exact historical card/version snapshots effective at each relevant case cutoff;
- actual prompt-assembly/runtime records proving which card fields were visible to the model;
- long-term rule versions and applicability windows at the same cutoff;
- immutable timestamps, source/version identifiers and hashes sufficient to bind each snapshot to the corresponding frozen case and source record.

Metadata such as card creation/last-edit time, export-time card text, or a current card snapshot is not proof of what the model actually saw at inference time.

If runtime snapshots or version history do not exist, record `SOURCE_UNAVAILABLE` / `HOLD` with the exact missing proof. Do not reconstruct or backfill historical facts from present-day cards.

### W3 — Resolve aliases, events and transitive world-component closure

Use source-backed evidence, not another lexical-only pass:
- adjudicate the three already-flagged pairs only if W1/W2 identifies new provenance not included in the earlier W17 review;
- reconcile the previously documented old 04→07 confirmed edge with the two transitive known old links reported in the 2026-11-19 inventory; do not assume these are three distinct edges;
- resolve or explicitly bound the possible transitive connection from the old component to R50 W17;
- distinguish shared platform/template text from character, organization, setting, event, timeline or plot continuity;
- keep every unsupported edge `INSUFFICIENT_EVIDENCE` and the overall graph `HOLD`.

The Owner's statement that intended story worlds are independent is recorded evidence of intent, not a substitute for the source graph.

### W4 — ROLE12 policy and four-arm runtime contract (separate gate)

Do not rerun the completed structure audit. Obtain an explicit Owner decision on how the two adjacent User turns are interpreted, without merging or rewriting frozen history. Then verify the actual Base/v0.1/v0.2/v0.3-A runtime construction against one signed contract: role sequence, system/card/rule order, tokenizer/template pins, truncation, generation reserve, EOS/sampling and model-specific differences. Current state remains policy not approved and runtime parity not verified.

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
- approval of the consecutive-User interpretation policy;
- approval of the four-arm runtime/role contract;
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
1. a source-to-evidence crosswalk showing what is already covered and what is genuinely new;
2. a timepoint card/rule provenance result with evidence pins or explicit `SOURCE_UNAVAILABLE`;
3. an alias/event/transitive component closure ledger with unresolved edges preserved as HOLD;
4. a separate ROLE12 Owner decision and four-arm parity status;
5. a refreshed gate matrix and next-owner-action list.

Every claim must identify its evidence tier: independently verified repository artifact, Owner-local SAFE receipt, Owner testimony, or agent inference. Never upgrade an Owner-local receipt to an independent source replay.

**Final state until all gates are independently closed and separately authorized:**
```text
WORLD_SEMANTIC_ISOLATION = HOLD
TIMEPOINT_CARD_RULE_PROVENANCE = PENDING
HIDDEN_ALIAS_WORLD_COMPONENT_CLOSURE = HOLD
CPU46_TOKEN_LENGTHS = VERIFIED_DRAFT_ONLY
ROLE12_STRUCTURE = PASS_AS_REPORTED
ROLE12_POLICY = NOT_APPROVED
FOUR_ARM_RUNTIME_ROLE_PARITY = NOT_VERIFIED
OFFICIAL_HELDOUT_ADMITTED = 0
FINAL_SEAL = NOT_PERFORMED
GPU_USED = false
MODEL_INFERENCE_RUN = false
TRAINING_RUN = false
```
