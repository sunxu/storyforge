# StoryForge R50 role12 local validation: implementation prepared (NOT RUN ON PRIVATE INPUT)

Date: 2026-10-23. A read-only Mac stdlib audit for the protected R50 46-case PRESEAL candidate set has been constructed and run against **20 synthetic unit tests**, all passed. No real 46-case data was accessed by the assistant, no Hugging Face Job or model inference was started, and no result on the actual 12 trailing-User cases is claimed.

## Canonical code and existing evidence

- Earlier protected audit-branch implementation: `audit/r49-r50-source-intake-20261015:scripts/v03_r50_cpu_tokenizer_preflight_46.py`, Git blob `c546194bd02608e921d9c673fa3e549c022468ae`. Its `make_messages` builds System+card+rules, preserves all historic roles/content/order and appends one User, **without merging consecutive User roles**.
- The audit branch `docs/evidence/V03_R50_46_CPU_TOKENIZER_VERIFIED_20261016.json` already reports 46 candidate cases, 364 historic messages and 12 trailing-User histories from a historical HF CPU tokenizer job. This is historical source evidence, not proof of newer CPU46 job's role correspondence.
- New Job `6ada3f1d925af0e27d4f569f` Owner-private report SHA256 `56aeac340ac1c0be1d0000314bcbdc72abd2f59582d643eee9e50698529f748e`; Owner local intake SHA256 `9b922c53cdafab11bd523e9c70f71a66a45d631da2b033487f2320b4150fe781`. Draft length 46/46 under 14848, from previous count-only receipt.
- The prepared read-only audit additionally pins tokenizer SHA256s and Qwen chat template SHA256 from historical verified artifact: tokenizer.json `0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3`, tokenizer_config.json `b11349aafa7cdc6a320767cf7ceb29ed82f7eda5d65e8e0819e76f0ce947bf27`, chat template `c3cf9e34abf4f9e36c2d72165aa9c132d3e2a725b6c2586aaa3a8af9d7a81041`.

## Prepared check

Use `scripts/v03_r50_role12_owner_audit.py` with the frozen candidate JSONL, frozen System, protected CPU46 report, and current Owner intake receipt **all on the Owner Mac outside Git**. The auditor independently replays the published builder, verifies SHA256 pins and exact per-case history counts/roles/trailing-User flags against the returned real tokenizer report. Checks for 12/12 trailing-User records with real input-ID digests and for 46/46 inputs within the *unapproved draft* token budget. Its output is count-only, stored outside the repository. It neither imports Transformers nor starts an HF Job. Use the accompanying `tests/test_v03_r50_role12_owner_audit.py` and `docs/R50_ROLE12_OWNER_LOCAL_REPLAY_CN.md`.

**Current result on real private R50 files:** NOT RUN, no PASS asserted. Any schema mismatch, tokenizer hash change, message count mismatch, extra/missing record or missing encoding digest yields HOLD.

**Critical interpretation:** Even a clean owner-machine count-only receipt would establish only current frozen **draft input construction** and actual Qwen tokenizer acceptance of the 12 User→User turns; four-arm inference-role semantics and actual deployment parity are NOT established. Cross-world semantic isolation remains HOLD; final seal false; official heldout admitted 0; GPU/inference/training/promotion not authorized.

Status: `R50_ROLE12_LOCAL_AUDITOR_SYNTHETIC_20_OF_20_PASS__REAL_PRIVATE_AUDIT_PENDING__ROLE_SEMANTICS_HOLD__NO_FINAL_SEAL`.
