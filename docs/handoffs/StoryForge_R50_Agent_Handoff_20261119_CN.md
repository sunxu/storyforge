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
| Consecutive User policy | PENDING OWNER DECISION on exact contract |
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
4. **W4 separate gate:** obtain the Owner's explicit decision on this exact consecutive-User contract. Only after that decision, perform read-only Base/v0.1/v0.2/v0.3-A runtime role/template parity verification. Do not mutate frozen messages.

   > 12 条历史末尾的 User 消息与新追加的 User 消息，是两条独立的连续 User turn。四个模型臂均原样保留两条消息，不合并、不改写、不删除，并将其作为统一输入合同的一部分。

   Until the Owner explicitly approves or rejects it, policy remains `PENDING_OWNER_DECISION`; silence is not approval.
5. Prepare preregistration only after the gates close. No final seal or inference without separate Owner authorization.

No HF Job, paid tokenizer job, GPU, model inference or training is needed or authorized for this handoff. If W1 finds no new evidence, preserve HOLD instead of generating another review that cannot change the decision.

## 6. Required first response from the new agent

Before making changes, report:
- current `main` HEAD and current state of PR #32;
- which cited artifacts were actually fetched and read;
- a no-repeat matrix marking each completed task;
- the W1 crosswalk plan, the existing-source locations searched for W2, the W3 trigger condition, and the pending exact ROLE12 Owner decision;
- whether any proposed operation would access private R50 content, paid HF, GPU, inference, training or frozen inputs.

Do not ask the Owner to repeat information already in this packet. Ask only for the specific missing evidence or authorization after repository and artifact checks are complete.

## 7. Privacy and execution boundary

- Raw R50 candidate JSONL, story text, target replies, case IDs, source-message IDs, private source mappings, answers and per-case tokenizer rows remain in the Owner-controlled private environment.
- GitHub receives only sanitized aggregate receipts and evidence pointers.
- Source inspection, if later authorized, is Owner-local and read-only. Return only allowlisted aggregate SAFE output.
- No database writes, source mutation, prompt rewriting, role coalescing, truncation, GPU, paid HF Job, model inference, training, answer-key access, final seal or promotion.
- Keep R50 separate from R56/R60 development, Base336 and other evaluation workstreams unless the Owner explicitly expands scope.

**Handoff state:** `R50_W1_CROSSWALK_FIRST__W2_EXISTING_SNAPSHOT_SEARCH_PARALLEL__W3_CONDITIONAL__W4_OWNER_DECISION_PENDING__NO_FINAL_SEAL`.
