# StoryForge R52/v0.3 — Owner selects full 41-case candidate scope

Date: 2026-10-21

Status: `OWNER_SELECTED_ALL41_SCOPE__NO_ADMISSION__NO_SPLIT__NO_GPU`.

## Scope decision

The owner explicitly instructed **“使用全部 41 条候选”** in response to the choice between retaining all 41 candidate cases or limiting the pool to the 18 without exact R45 Train/Validation target repeats. Accordingly, retain all **41** in the intended R52/v0.3 **candidate pool** and retain R45 history labels; do not filter out previously repeated targets solely to reach an artificial novelty target.

This **is not** blanket approval of 41 cases for training. The original Owner worksheet remains byte-identical, with per-case content/safety/age/consent and independent world/rights signoffs pending. No formal Train/Validation JSONL is produced. No paid CPU/GPU authorization is inferred.

## Source-bound count-only check

Verified source ZIP `R52_OWNER_41_FINAL_CASE_DECISION_INTAKE_PRIVATE_20261021.zip` SHA256:
`71388f8eacb57673d9ad13027abf25469633fe71fd8a0b8d660c8e3634e146f1`

Its original 46-case worksheet SHA256:
`f3a880bf17fa2f8285ac70f067f0f0a913886813189c2674a1d464b5956f7f96`

- **41** eligible for Owner final case-by-case gate review; **5** excluded HOLD (3 substantive quality defects, 2 targeted soft concerns).
- Among the 41: **14** exact R45 Train target repeats, **9** exact R45 Validation target repeats, **18** with no exact target match. The latter 18 are **not** certified truly unexposed.
- Owner declaration confirms all seven stories independent, original, usable for training, and characters adult. Those declarations do not replace target-specific safety and consent checks.

Private ID+target-hash selection and proposed partitions are in **conversation-only** `R52_OWNER_ALL41_SCOPE_SELECTED_PRIVATE_20261021.zip`, SHA256:
`73384088282088e942f29d61bef022d4a3833889a39b7e3f644b682c05c81c65`.
Never commit the private ZIP or any sample IDs/target bodies to ordinary Git.

## Optional split plan for consideration only

Provisional Scenario B: **31 Train / 10 Validation**, with the 10 Validation candidates from Owner-attested independent story ranks **06** and **13**. This is a count/membership *proposal*, not an actual release/split. Unlike the 33/8 one-Validation-world proposal, it covers two Validation worlds and has zero **exact target** repeats from R45 Train or Validation within this proposed Validation set. But rank 06 shares an **R45 Train story UUID**, so this is not a claim of model-unseen world evaluation; old R45/R46 data lineage must be clearly disclosed, and formal independent R50 heldout remains sealed.

Never claim all 41 examples are gradient-updated training cases: under this proposal 31 would be Train and 10 would be within-run Validation, if all later passed the gates. No zero-leakage claim can be made until world components are formally source-bound and signed.

## Remaining gates

- Case-level quality/consent/adulthood/safety/rights evidence with independent backing; 0/46 Owner final signoffs.
- World-component source-bound signoff; 0/7 independently certified.
- True R45/R46 actual runtime exposure reconciliation and exact final split, if approved.
- R53 real pinned Qwen tokenizer, chat-template, ms-swift collator and final-only label mask; not yet completed.
- Separate explicit paid GPU authorization; none granted.
- Preserve `PENDING_NOT_APPROVED`, `split=null`, R50 unopened, and no new GPU jobs.

**No frozen story target, private reviewer record or Gold source was rewritten.**
