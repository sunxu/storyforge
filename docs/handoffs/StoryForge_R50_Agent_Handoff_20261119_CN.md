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
| Prior W17 AI pair adjudication | Same three pairs; all `INSUFFICIENT_EVIDENCE` |
| Seven W17 full-message gaps | All `INSUFFICIENT_CONTEXT` |
| Timepoint card/rule actual inference proof | PENDING / NOT CERTIFIED |
| Hidden alias / event / transitive world closure | HOLD |
| CPU46 token lengths | 46/46 within Draft budget |
| ROLE12 structure | 46/46 roles/order; 12/12 trailing User encoding reported |
| Consecutive User policy | NOT APPROVED |
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

## 5. The only productive next work

1. Crosswalk the 2026-11-19 inventory with the W17 evidence and source manifests. Determine whether it contains genuinely new provenance.
2. Resolve the timepoint gap using authenticated historical inference-time card/rule snapshots and prompt-assembly/runtime records. Metadata timestamps or current card content are insufficient.
3. Resolve alias/event/transitive world components using new, independently citable source evidence. Include the already known 04→07 edge and two known transitive old links. If proof is unavailable, keep HOLD and state exactly what is missing.
4. Separately obtain Owner approval for the consecutive-User interpretation and verify actual four-arm runtime role/template parity. Do not mutate the frozen source.
5. Prepare preregistration only after evidence gates close. No final seal or inference without separate Owner authorization.

If no new provenance exists, stop repeated review. Produce a concise `NO_NEW_EVIDENCE` result and preserve HOLD rather than generating another AI review that cannot change the decision.

## 6. Required first response from the new agent

Before making changes, report:
- current `main` HEAD and current state of PR #32;
- which cited artifacts were actually fetched and read;
- a no-repeat matrix marking each completed task;
- the exact new evidence required for W1–W4;
- whether any proposed operation would access private R50 content, paid HF, GPU, inference, training or frozen inputs.

Do not ask the Owner to repeat information already in this packet. Ask only for the specific missing evidence or authorization after repository and artifact checks are complete.

## 7. Privacy and execution boundary

- Raw R50 candidate JSONL, story text, target replies, case IDs, source-message IDs, private source mappings, answers and per-case tokenizer rows remain in the Owner-controlled private environment.
- GitHub receives only sanitized aggregate receipts and evidence pointers.
- Source inspection, if later authorized, is Owner-local and read-only. Return only allowlisted aggregate SAFE output.
- No database writes, source mutation, prompt rewriting, role coalescing, truncation, GPU, paid HF Job, model inference, training, answer-key access, final seal or promotion.
- Keep R50 separate from R56/R60 development, Base336 and other evaluation workstreams unless the Owner explicitly expands scope.

**Handoff state:** `R50_WORLD_SEMANTIC_HOLD__TIMEPOINT_PROVENANCE_PENDING__ROLE12_POLICY_HOLD__NO_FINAL_SEAL`.
