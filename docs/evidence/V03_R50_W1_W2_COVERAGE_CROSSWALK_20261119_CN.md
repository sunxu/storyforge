# StoryForge R50 — W1/W2 historical-evidence coverage crosswalk (2026-11-19)

**Repository:** `sunxu/storyforge`  
**Prepared against:** `main` HEAD `c7f0161b0c99d87cf6ec5f5ea453f61c6d042cbf`; source baseline commit `a197923e1e15344e8c98bd96e593e84781b68c83`.  
**Publication:** proposed documentation on `docs/r50-agent-handoff-20261119` (Draft PR #33); not merged.  
**Evidence policy:** this document contains only repository references, hashes, counts, rank-level references already present in approved safe summaries, and gate states. It contains no story text, case IDs, source-message IDs, private mappings, answers, or per-case data.

## 1. Executive result

- **W1:** `NO_NEW_EVIDENCE__EXISTING_W17_FLAGS_RECONFIRMED`. The 2026-11-19 inventory's three flagged pair rows are the same three old-rank/new-rank pairs already adjudicated on 2026-10-19. The new inventory adds broader source-volume and identity/lexical counts, but the sanitized record does not expose a new source-backed alias, event, card version, rule version, or inference-time prompt snapshot that would change an existing pair decision.
- **W1 binding gap:** the 2026-11-19 aggregate reports two transitive old links but does not expose their rank-pair identities. The prior W17 safe summary separately records the old 04→07 edge and a possible transitive link to W17 as `INSUFFICIENT_EVIDENCE`. The current safe materials do not prove whether 04→07 is one of those two links or a separate edge. Do not count these as three distinct edges.
- **W3:** `NOT_TRIGGERED`. No new source-backed provenance was found to justify reopening the same three pair reviews or seven full-message gaps.
- **W2:** `SOURCE_UNAVAILABLE_IN_SEARCHED_SOURCES` for actual inference-effective card/rule snapshots and prompt-assembly/runtime receipts. Existing export-time card material, source-message rule references, and saved runtime checkpoint metadata are not proof of the exact content assembled into a model request at each cutoff.
- **W2 scope limitation:** searched the current GitHub repository/source tree and the available R50 Library artifact inventory. No direct Owner Mac filesystem or private cloud-storage mount was available; therefore this is not a claim that no such artifact exists anywhere.

## 2. Evidence crosswalk

| Evidence family | Pinned artifact / source | Previously covered scope | 2026-11-19 reconciliation | W1 disposition |
|---|---|---|---|---|
| Frozen R50 source replay | `audit/r49-r50-source-intake-20261015`, source commit `a197923e1e15344e8c98bd96e593e84781b68c83`; `docs/evidence/V03_R50_REAL_SOURCE_REPLAY_20261016.json` (blob `0fe535f1a40d1730f5e33abcbfaf6d843b13ea1e`) | 50/50 source cases; 392/392 historical references; 50/50 card-reference/effective-interval checks. The receipt explicitly did not certify full card facts, full rule applicability, semantic aliases, R45 isolation, or final admission. | The 2026-11-19 owner inventory covers 50 source-pair rows and larger full-source byte counts. It does not supersede the source replay's narrower checks or upgrade its pending semantic/timepoint gates. | Existing evidence; no new semantic closure |
| Owner 50→46 selection | Frozen input SHA256 `109642a6c0e27895ae83274bec79ec9f53d922e407ca435431acf3f31a31e1f2`; 2026-10-22 preseal delta receipt on main | Original 50 immutable; 4 excluded; 46 PRESEAL; five group counts 9/10/9/8/10; 364 historical messages; 12 trailing-User histories. | The 2026-11-19 audit does not report a changed candidate set or modified source. | No change; preserve frozen input |
| 2026-11-19 full-source inventory | `docs/evidence/V03_R50_WORLD_CPU46_ROLE12_AUDIT_20261119_CN.md`, PR #32 branch; blob `a3523e94ea6c6d2802e564d85f85defc88c156bf` | Owner-reported: 50 source-pair rows; 37,165 old-source messages; 11,627 R50-source messages; Old14 numbered-chat sources 14; Old06_15 and Old14 CRC PASS; 3 exact-long-message flagged pair rows and 3 sampled 120-character flagged pair rows; 0 same-Story-ID pairs; 0 extra archive Source-ID conflicts. | All three flagged rows are the same scoped W17 pair set already reviewed. These counts are Owner-supplied SAFE results, not an independent replay of the private inventory bytes. | No new pair set; no new source-backed adjudication |
| W17 pair dossier | `docs/evidence/V03_R50_W17_AI_SEMANTIC_DECISION_SAFE_SUMMARY_20261019.json`, audit branch; blob `952307a2e84a38e08796a1e1888246f3f2420e2a` | Three pairs: old ranks 2, 4, and 10 against R50 rank 17; evidence-pointer counts 9, 9, and 8; all three `INSUFFICIENT_EVIDENCE`; reviewer independence/correctness not script-verified. Shared literal was classified as platform/template text. | Taskbook and latest inventory reconcile the three current flags to this same pair set. No new pair or new cited source version is recorded. | Already reviewed; do not repeat |
| W17 seven full-message gaps | `docs/evidence/V03_R50_W17_FULL_MESSAGE_AI_REVIEW_OWNER_RECEIPT_20261019.json`, audit branch; blob `c67b53169606d21e81af1dac33b1b676e4e314a5` | Seven gaps; 344 dossier message entries; 75 scoped citations; all seven `INSUFFICIENT_CONTEXT`; historical card timings not checked; exact inference card snapshot false; old 04→07 component unresolved. | The 2026-11-19 aggregate supplies no new full-message citation, historical card version, or runtime request record that changes any of the seven decisions. | Already reviewed; do not repeat |
| W17 timepoint metadata | `docs/evidence/V03_R50_W17_TIMEPOINT_METADATA_OWNER_RECEIPT_20261019.json`, audit branch; blob `91b61454106d8de479bdbb256ba0ba008f6a9470` | 70 W17 dossier entries; 26 W17 citations; 16 distinct cited original messages; historical content-version count 0; moderation-snapshot count 0; exact inference-effective card fields `NOT_CERTIFIED`. Export-card metadata predates the chat, but the export observation is after the chat. | The 2026-11-19 inventory does not add a historical content version or a request-time card snapshot. | Timepoint gate remains pending |
| Old archive / source manifests | Frozen source commit `a197923...`; `evaluations/v0.2/source-archives/06-15/source_bundle_manifest.json` (blob `d83e609c0b529ad8892200a86a05dbd779e9e9c2`); `evaluations/v0.2/source-archives/16-20/` source tree | The 06-15 manifest pins ten raw source archives and their hashes. The 16-20 source tree contains the five R50 source exports and associated card/runtime-context files. | The 2026-11-19 result reports Old06_15 and Old14 CRC PASS, but the sanitized report does not provide rank-level links for the two transitive old edges or a new source-version delta. | Integrity reported; graph edge binding remains open |
| Frozen R45 Train49/Val15 | Owner runbook pins Train SHA256 `e7442993088617c4eaefd3a0c9efc7651932f7048f34586046bf6d5b5981a742` and Validation SHA256 `5ebbb3c6986a5ac4d294175bab1980ee61df08536f9b8438c8a67010630f1963`; main safe receipt `V03_R50_OWNER_R45_FULL_SOURCE_GATE_COUNTS_ONLY_20261022.md` | Owner-reported exact source screen PASS for 49/15 and zero exact overlap counters; receipt itself says it is not semantic independence PASS and was not independently rehashed in GitHub. | Latest inventory reports 9 R45 source ranks checked. It does not publish the rank-level edge mapping or raw R45 bytes. | Exact overlap screen remains Owner-reported; semantic closure HOLD |

## 3. Transitive-edge reconciliation

The existing W17 pair safe summary records:
- one previously confirmed old edge, 04→07;
- a possible transitive link from that old component to W17, still `INSUFFICIENT_EVIDENCE`.

The 2026-11-19 inventory reports `transitive_known_old_links=2`, but the public SAFE reconciliation does not include the two rank-pair identities. Therefore:

1. It is not possible to establish from the available safe record whether 04→07 is one of the two links or is additional to both.
2. It is not valid to infer three separate edges.
3. No transitive path to W17 is newly proven by the aggregate count.
4. The overall hidden-alias/world-component graph remains `HOLD`.

**Smallest additional read-only check, only if the Owner wants this bookkeeping gap closed:** from the already-existing private inventory, emit a SAFE aggregate containing the two old-link rank pairs only (rank numbers, no IDs/text), a boolean indicating whether 04→07 is among them, and the source-manifest SHA256 pins used for those rows. Do not rerun the source scan, CRC, lexical screen, or AI review.

## 4. W2 existing-snapshot search

### Sources searched

1. GitHub `main` at `c7f0161b0c99d87cf6ec5f5ea453f61c6d042cbf`, plus frozen source commit `a197923e1e15344e8c98bd96e593e84781b68c83`.
2. The R50 source tree `evaluations/v0.2/source-archives/16-20/`, including the existence of source exports, `story-cards.json`, and `runtime-context.json` artifacts.
3. Existing R50 evidence and the available Owner Library inventory of 106 R50 artifacts, including the W17 semantic kit, seven full-message dossiers, private source index, CPU46 receipts, R45 full-source gate output, and frozen R50 selection artifacts.
4. Existing `R50_REVIEW_KIT_PREFLIGHT_20261016.json` and `R50_AUTHORING_REPORT.md` metadata about card-provenance kinds and the intended card source type by world.
5. The W17 pair, full-message, and timepoint SAFE receipts listed above.

### Findings and limitations

| Artifact type | Existing evidence found | Does it prove what the model saw at the case cutoff? |
|---|---|---|
| Export-time card | W17/W18 are described as using export-time cards; W17 export-card metadata predates the first chat message. The card was observed/exported after the last chat message. | **No.** It is not a versioned historical content snapshot or an inference-request capture. |
| Historical card content versions | Review-kit preflight reports 20 content-version provenance items across the 50-case kit, but the W17 timepoint receipt specifically reports 0 historical content versions for the reviewed W17 scope. | **No for W17.** Do not allocate aggregate counts to W17 without case-bound provenance. |
| Moderation/source snapshots | Review-kit preflight reports 10 moderation-source snapshots across the 50-case kit; W17 timepoint receipt reports 0 for W17. | **No for W17.** |
| Saved runtime context | The rank-17 source archive contains a `runtime-context.json` checkpoint artifact. Its own note distinguishes saved checkpoint stage/state from a model request snapshot. | **No.** A checkpoint is not an inference-time prompt capture. |
| Long-term rule source messages | Existing source replay/authoring evidence identifies prior source-message support for selected rules in five cases; content-scope manual review remains pending. | **Partial source provenance only.** It does not prove the complete rule set, applicability, or exact system prompt injected at runtime. |
| Prompt-assembly/runtime receipt | No per-case inference request snapshot or immutable prompt-assembly receipt was found in the searched R50 artifact inventory or GitHub source tree. | **No; mark unavailable in searched sources.** |

**W2 result:** `SOURCE_UNAVAILABLE_IN_SEARCHED_SOURCES__TIMEPOINT_CARD_RULE_RUNTIME_PROOF`.

This is a bounded search result, not proof that no such artifact exists in any Owner-held storage. The next action is not to reconstruct historical prompts or request a new export. If the Owner knows of an existing protected location, identify that exact location/ref and search it read-only; otherwise preserve `SOURCE_UNAVAILABLE` / `HOLD`.

## 5. No-repeat and gate disposition

| Work item | Disposition |
|---|---|
| Old06_15 / Old14 CRC | `ALREADY_DONE`; do not rerun |
| 2026-11-19 50-row source inventory / lexical screen | `ALREADY_DONE`; do not rerun |
| Three W17 pair adjudications | `ALREADY_DONE`; do not repeat on unchanged evidence |
| Seven W17 full-message reviews | `ALREADY_DONE`; do not repeat on unchanged evidence |
| R45 Train49/Val15 full-source screen | `ALREADY_DONE_AS_OWNER_REPORTED`; no duplicate run |
| CPU46 Tokenizer 46-length job | `ALREADY_DONE`; no repeat job |
| ROLE12 structure/tokenizer audit | `ALREADY_DONE`; no repeat audit |
| Historical card/rule/request snapshot search | `NEW_EVIDENCE_REQUIRED`; current searched sources return bounded `SOURCE_UNAVAILABLE` |
| Old-link rank-pair binding | `NEW_EVIDENCE_REQUIRED`; one small SAFE aggregate only if Owner can produce it from existing inventory |
| W3 semantic adjudication | `NOT_TRIGGERED` |
| W4 exact consecutive-User policy | `APPROVED_BY_OWNER_2026-11-19` |
| Four-arm runtime parity | `NEW_EVIDENCE_REQUIRED`; policy is approved, actual runtime/load receipts remain unverified; read-only only, no inference |
| Final seal / admission / promotion | `NOT_AUTHORIZED`; admission remains 0 |

## 6. Refreshed gate matrix

```text
W1_CROSSWALK = NO_NEW_EVIDENCE__EXISTING_W17_FLAGS_RECONFIRMED
W1_EDGE_IDENTITY_BINDING = INCOMPLETE__TWO_LINK_RANK_PAIRS_NOT_IN_SAFE_RECORD
W2_TIMEPOINT_CARD_RULE_RUNTIME = SOURCE_UNAVAILABLE_IN_SEARCHED_SOURCES
W3 = NOT_TRIGGERED
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

No private source bytes were changed or copied to Git. No CRC, lexical scan, tokenizer job, AI review, model inference, GPU job, training, answer-key access, or final seal was run for this crosswalk.


## 7. Subsequent W4/Original Gold decisions (2026-11-19)

This crosswalk's original W1/W2 findings are unchanged. Later Owner decisions supersede only the ROLE12 policy status:

- Owner explicitly approved the exact consecutive-User contract: `ROLE12_POLICY = APPROVED`.
- Actual Base/v0.1/v0.2/v0.3-A runtime parity remains `NOT_VERIFIED`; approval is not runtime evidence.
- Original Gold is required as a comparison reference when exact source alignment exists. The R50-specific contract is `docs/plans/V03_R50_FOUR_MODEL_PLUS_ORIGINAL_GOLD_CONTRACT_20261119_CN.md`. R50 remains prompt-only in the known schema, so exact Gold coverage is `NOT_ESTABLISHED`; report `N_gold / 46` and keep unmatched cases in the four-model denominator.
- No prior W1/W2, CRC, lexical, AI, tokenizer, or ROLE12 structural audit was repeated.


## 8. Original Gold source availability reconciliation

A separate SAFE receipt records the Owner-provided archive integrity output and bounded Original Gold finding: `docs/evidence/V03_R50_ORIGINAL_GOLD_SOURCE_AVAILABILITY_20261119_CN.md`.

The pinned 2026-10-16 R50 replay has `source_input_normalized_verbatim_reuses=0` across all 50 new User inputs versus the five R50 source transcripts. Therefore no exact current-User-input Original Gold is available from those pinned five transcripts, including the protected 46 subset. The 14-chat and 06–15 archives are now Owner-verified for integrity but have not been checked for exact full-history matches. This does not trigger W3 and does not change WORLD or timepoint HOLDs. Overall Gold coverage remains `NOT_ESTABLISHED` pending any additional exact full-history source lookup.
