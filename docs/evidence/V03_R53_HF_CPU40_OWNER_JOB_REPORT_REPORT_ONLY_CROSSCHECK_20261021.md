# StoryForge R53 — HF CPU40 returned report: frozen-source cross-check accepted, runtime log pending

Date: 2026-10-21 (Asia/Singapore)

**Current evidence state:** `HF_CPU40_REPORT_AND_STAGE_40_CASES_CROSSCHECK_PASS__ORIGINAL_RUNTIME_LOG_PENDING__OFFICIAL_VERIFIER_EXIT_2__FORMAL_TRAIN_VAL_0_0`.

The Owner reported Hugging Face CPU Job `6ad8a7af0a35baab53a1ced2` completed and provided terminal markers:
- `R53_STATUS= R53_HF_CPU40_REAL_TOKENIZER_COLLATOR_MASK_PASS__NO_DATA_ADMISSION`
- `R53_HF_CPU40_WORKER_EXECUTED_NO_TRAIN`

Original uploaded confidential `R53_HF_CPU40_AUDIT_REPORT_PRIVATE.json` (retained outside ordinary Git): SHA256 `8624c21b6d9fff5e74006bca000c69f0d39870f1fb030c2ff4fb96cc523f1f45`; 40 audited rows. Run key `r53-cpu40-20261021T113539Z-523139`.

## Actual independent local checks

The earlier immutable 31 Train / 9 Validation source stage was reloaded, and the original R53 CPU auditor's `preflight` actually executed successfully. Entire private source byte hashes, compiled training-message byte hashes and stage manifest matched the returned report.

- Actual uploaded report: **31/31 Train and 9/9 Validation**, exactly **40 distinct IDs**, source-pinned target SHA256 and split exactly matching local frozen 31/9.
- All **40** results state `REAL_LAST_ASSISTANT_AND_COLLATOR_PASS`; each has plausible token counts and a 64-hex SHA256 label digest.
- **Train**: 67,491 native tokens, 8,932 supervised tokens; max native sample **3,668**.
- **Validation**: 15,285 native tokens, 2,298 supervised tokens; max native sample **2,535**.
- Overall supervised tokens: **11,230**. All samples below 16,384 tokens.
- Report states pinned `Qwen/Qwen3.8-27B@1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`, `ms-swift==4.5.3`, `transformers==5.16.1`, no training/GPU/R50 usage and no dataset admission.
- Reporter `auditor_script_sha256` matched an actual local hash of original staged auditor: `97afde362779dc4eaa6c39e75340b138d749a6d5da559486af6ab4725cfa8f02`.

## Meaningful limitations requiring accurate wording

1. **Original worker runtime log was not uploaded**, only Owner's extracted completion lines and the private report. The project's unchanged official intake verifier (`scripts/v03_r53_hf_cpu40_verify.py`) **was actually invoked** with report + frozen source and a missing log, and correctly returned **exit 2**, issuing **no official PASS receipt**. Obtain the existing `R53_CPU40_RUNTIME_LOG_PRIVATE.txt` and SHA256 sidecar from the same private Bucket; **do not rerun paid CPU**. Rerun official intake locally with those originals.
2. All **40/40** report fields `transformers_vs_swift_input_identical` are `false`; native token counts differ by 45–62 tokens. This is **not proof of native ms-swift label-mask failure**, but should not be concealed or treated as identical renderings. Model invocation format may require future parity study.
3. The actual real collator was called with **one case per batch**, so all `padding_tokens=0`. This checks singleton collator consistency; actual multi-item nonzero padding was covered only by earlier offline regressions, not this remote Job.
4. Neither original remote token arrays nor the complete seven HF Job files were independently downloaded into this local conversation. The report itself and all local original case targets are byte-cross-checked, which differs from independently reproducing remote tokenization.
5. Other release gates (rights/provenance per adopted policy, final exact-byte data release approval) remain separate. This is not authorization to train, publish, touch R50, or use GPU. Formal Train **0** / Validation **0**.

Safe machine-readable report-only cross-check `R53_HF_CPU40_REPORT_ONLY_CROSSCHECK_SAFE_20261021.json` was generated locally with no candidate IDs or story text, and is a conversation artifact only.
