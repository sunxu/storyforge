# StoryForge v0.2 — R43.3 uploaded HF CPU actual collator JSON cross-check

Date: 2026-10-14. **Uploaded JSON cross-check PASS; this is not final dataset training release.**

## Exact evidence reviewed
- User-uploaded full JSON `R43_HF_RUNTIME_REPORT_PRIVATE_v2.json`, 22,184 bytes, SHA256 `c5eef38cf8cb86892b6dcba51ae8cc8f29bc4d6df7b90c0210fc6decb226ab34`.
- Frozen private R43 stage ZIP SHA256 `6728ffc81f98e1f5b8db098ec40a09442ef7e8b77e888e5f535fd9bbfe21412a`; ZIP CRC PASS. Source R42 ZIP SHA256 `a77e3519f9f81c45cc4dfe68b07c6330a615a1258fb0abac750d6186f5a593e2`; ZIP CRC PASS.
- Actual uploaded JSON reports `ACTUAL_COLLATOR_PASS_NO_TRAINING_APPROVAL`; `ms-swift==4.5.3`, `transformers==5.16.1`, `tokenizers==0.23.3`, `huggingface-hub==1.33.0`, model revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`.

## Independent offline cross-check findings
- Train: 56/56 PASS, exactly matched frozen 56 sample IDs **in file order**, unique IDs, local target hash checks passed. Frozen preview SHA256 `d94eaf861d7d86951c1ab0e60dbb38fb006998e9a6a035c19c544ba4d44862ee`. Reported supervised tokens **14,373**, max template length **3,298**.
- Validation: 16/16 PASS, exact IDs/order, local target hashes verified. Frozen preview SHA256 `87eb9f6a4b552c681edbfe3977af07c3a205234ad76f6de42810aa749a8fb47a`. Reported supervised tokens **4,434**, max template length **3,694**.
- 72 total sample IDs unique; 72 per-row label hash strings valid 64-character SHA256; all nonzero supervision; lengths <=16,384. Total supervised tokens **18,807**, actual template tokens **136,793**.
- Tokenizer-only counts exceed actual ms-swift template counts by 46/50/54/66 tokens depending on record; not a release failure. Full report says `training_performed=false`, `gpu_authorized=false`.

## Critical evidence boundary
The uploaded report **does not contain remote input file SHA256s or HF Job ID**. Thus per-row ID/order and local SHA verification **do not independently prove all remote input bytes were identical to locally frozen files**. HF Job ID `6acf00c75ccb47ba0f790ae8` and its private bucket report path remain earlier **owner-reported** provenance; they are not embedded in the JSON. The per-row label digest values reflect an actual remote run as reported, but have **not been independently recomputed using ms-swift** in this environment. This is sufficient to close the previously blocked **remote CPU preflight report-content** task, not the overall training-admission release.

## Remaining genuine blockers
1. Full-history canon/semantic review and global alias/world noncontamination approval.
2. **0 fresh independent sealed heldout**. Previously exposed v0.1 test data or assistant-authored prompts cannot count.
3. Explicit final dataset admission, and separate GPU authorization. **0 approved Train/Validation/Test, GPU not launched.**

## Private offline re-verification artifact
`StoryForge_R43_3_Report_Verification_20261014.zip` includes `verify_r43_uploaded_report.py`, `R43_HF_Independent_Crosscheck_20261014.json`, `README.md`, and SHA256 manifest. It does not contain original confidential source text. No raw report uploaded to ordinary Git.

**Outcome marker: `R43_3_ACTUAL_COLLATOR_REPORT_CONTENT_72_72_CROSSCHECK_PASS__GPU_NOT_APPROVED`**.
