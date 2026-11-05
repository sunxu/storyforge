# StoryForge v0.2 — R43.1 CPU preflight BLOCKED triage & helper repair

Date: 2026-10-14. User's remote console only displayed `R43 HF CPU Collator: BLOCKED; GPU/Training not launched`. **The precise remote cause is not known until reading the remote JSON report**; do not promote `BLOCKED` to PASS.

## Verified bug in the shipped helper
The R43 `ids()` helper accepted a Python `dict` but not a generic `collections.abc.Mapping`. Hugging Face `BatchEncoding` can implement `Mapping` without being a `dict`, yielding a false `Expected exactly one list[int] token sequence` rejection even for valid `input_ids`. A local `UserDict` stand-in reproduced the false rejection.

Fix: R43.1 diagnostic runner uses `Mapping`, checks for `input_ids`, normalizes exactly one batched sequence, rejects ambiguous multirow/empty/non-integer sequences, and prints the first blocked reasons. It preserves pinned tokenizer revision, ms-swift/transformers version requirements, full `hf_label_mask_audit.audit_row`, counterfactual target-masked verification, 16,384 token budget, original 56/16 immutable inputs, and actual collator verification.

## Local checks
- `R43.1 TOKEN_SHAPE_SELF_TEST_PASS`, including generic Mapping and -100 masked-label handling.
- Unmodified original `r43_gate.py` static 72-row stage: `STATIC_STAGE_PASS_NOT_TRAINING_APPROVAL`.
- Local actual ms-swift runtime remains intentionally `BLOCKED` because package `ms-swift` is unavailable here. We did not perform a real installed Collator test.
- Original R43 ZIP is unchanged. Patch artifact: `R43_1_CPU_Collator_Fix_20261014.zip`, SHA256 `af51e314d47cf8fee77be243e7e1af20d0cf4a57fd14318ae32d075ec3a441f1`. Private user-facing archive; no story text in patch.

## Remote use
1. Read existing `R43_HF_RUNTIME_REPORT_PRIVATE.json` and extract `error`, `traceback_type`, runtime version fields and first per-row errors. This may show a different blocker; **do not assume Mapping was the original cause**.
2. Place patched `r43_hf_actual_collator_no_train_v2.py` beside original `r43_gate.py` in the unpacked R43 folder.
3. Run `python3 r43_hf_actual_collator_no_train_v2.py --self-test` before dependency/network checks.
4. Re-run R43 no-train test against original 56/16 and produce `R43_HF_RUNTIME_REPORT_PRIVATE_v2.json`; check summary and reconcile sample count and labels.

## Training authorization
External independent heldout remains 0, and full final story-world semantics/alias certification not completed. **R43 runtime PASS, if eventually obtained, is not sufficient to approve GPU or model quality promotion.** No GPU launched or authorized by this repair.
