# StoryForge v0.2 — R43.2 HF CPU actual collator result (owner-provided remote report)

Date: 2026-10-14. **Runtime preflight: PASS AS REPORTED. Dataset admission: NOT APPROVED. Training: NOT LAUNCHED.**

## Submitted successful remote execution evidence
- HF Job ID: `6acf00c75ccb47ba0f790ae8`; user reports Job completed.
- Terminal status: `ACTUAL_COLLATOR_PASS_NO_TRAINING_APPROVAL`; global error: none; error type: none.
- Actual train partition: 56/56 PASS, failed=0. Actual validation partition: 16/16 PASS, failed=0.
- Remote versions as reported: `ms-swift==4.5.3`, `transformers==5.16.1`, `tokenizers==0.23.3`, `huggingface-hub==1.33.0`.
- Private report location: `hf://buckets/adradar/storyforge-training/preflight/v02-r43/results/r43-20261014T041047Z-26516/R43_HF_RUNTIME_REPORT_PRIVATE_v2.json`.
- These findings are based on the **project owner's pasted runtime summary**. The full private JSON report has **not** been downloaded or independently re-hashed during this chat turn. Therefore source-file SHA and per-example label counts are inherited expectations until those full report bytes are examined.

## Expected exact dataset identities from immutable R42/R43 staging
- Train 56, SHA256: `d94eaf861d7d86951c1ab0e60dbb38fb006998e9a6a035c19c544ba4d44862ee`.
- Validation 16, SHA256: `87eb9f6a4b552c681edbfe3977af07c3a205234ad76f6de42810aa749a8fb47a`.
- These are pinned **expected** candidate files; do not claim remote data SHA matches until confirmed by full job report or remote manifest.

## Engineering outcome and remaining blocks
- Earlier `PackageNotFoundError: ms-swift` resolved for this successful remote job, as evidenced by installed version and per-partition PASS status.
- The real target-only loss mask/actual CPU collator gate may now be marked `REMOTE_PASS_OWNER_REPORTED`, separate from `FULL_REPORT_BYTES_VERIFIED`.
- Project owner rights/age assertions remain accepted without requesting documents.
- Scope-limited story chronology, target fidelity, and known 04↔07 same-world boundary retain R42 results. **Complete hidden alias and complete-history canon signoff remain unresolved.**
- Genuinely fresh independent sealed human-authored Held-out count remains **0**; previously exposed v0.1 tests and assistant-authored tests do not qualify.
- Final Train/Validation/Test admission **0**; paid GPU authorization **false**; GPU/optimizer training **not started**.

## Recommended next evidence action
Download the exact private JSON report with HF CLI and record SHA256, inspect sample hashes, tokenizer model revision, runtime flags, sample counts, and no-training declaration. Supply independently authored held-out prompts before quality evaluation. Do not start GPU or treat a Collator PASS as model-quality promotion.

Result marker: `R43_REMOTE_COLLATOR_72_OF_72_PASS_OWNER_REPORTED__NO_TRAINING_APPROVAL`.
