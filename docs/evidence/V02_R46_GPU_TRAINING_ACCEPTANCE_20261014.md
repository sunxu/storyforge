# StoryForge v0.2 — R46 exploratory GPU run: engineering acceptance

**Date:** 2026-10-14.  
**Result:** `EXPLORATORY_GPU_SFT_PASS_NOT_PROMOTED` — a completed engineering **experiment**, **not a model-quality promotion**.

## Verified reported run identity

- **HF Job (owner-reported):** `6acf29e4c66288145223871b`, completed.
- **R46_RUN_KEY:** `r46-20261014T070529Z-248172`.
- **Base:** `Qwen/Qwen3.8-27B`, R46 pinned model revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0` (revision from immutable job contract; not repeated in the output report).
- **GPU:** `NVIDIA A100-SXM4-80GB` (reported device total 85,093,777,408 bytes). The `free_bytes` field is a gate-time availability measurement, **not** peak training VRAM.
- **Experiment:** one-epoch QLoRA rank 64 / alpha 128, NF4 BF16, lr 5e-5, batch 1, gradient accumulation 8, target-only `loss_scale=last_round`.
- **Inputs:** exact R45 49 Train / 15 Validation. No independent held-out touched. Owner-directed, bounded exploratory GPU run; original Gold 195 unchanged.

## Uploaded full result JSON & reproducibility

- Uploaded exact private report: `R46_TRAINING_REPORT_PRIVATE.json`, **2069 bytes**, SHA256 `4ad35faedc97724f588914f59d3a00293e681e2245d2d74c27d528e3179a8e83`. The private full report stays in the owner's local files and HF Bucket; only metadata is committed to ordinary Git.
- R45 private ZIP rechecked locally: SHA256 `da4b7718f1c1cbd0429553b684eeaf70f207fd2e41aae4e8fe0a52a11b647b9e`.
- Source R27 JSONL SHA256 `cdecc311f05e2c700f1038f3afca09c889ff681d4ef55dc18dc7426c9d14a92a`.
- Frozen R45 original-input Train (49): `e7442993088617c4eaefd3a0c9efc7651932f7048f34586046bf6d5b5981a742`.
- Frozen R45 original-input Validation (15): `5ebbb3c6986a5ac4d294175bab1980ee61df08536f9b8438c8a67010630f1963`.
- **Important additional check:** independently recreated each compiled target-only SFT JSONL from the exact R45 private files using the repository's `scripts/prepare_sft.py` transformation logic; both byte SHA256s matched the uploaded GPU report:
  - compiled Train: `a028bf9fb28b12b4a3fa352d6a60281bd9e1ef5773ebfdfecc7ac80eb2cba517`.
  - compiled Validation: `cc8d647471423f4969149f8cabdea980aad15d8bd4424d9dd98da3313c639f3c`.
- Job config SHA256 from report: `5fa33ce340e62c464a98550796cbb6c61f1164e5c90cd2689622cd1fe3fcabd3`. R46 config validation checked 20 fields.
- Prior R43 actual CPU Collator evidence covered the 64 immutable source examples; this run's Worker also invoked live compiled-data label audits before SFT, but the final JSON does **not** provide their complete per-token logs. Use the Job's logs for that stronger assertion.

## Training and Adapter acceptance (from original uploaded report)

- `training_started=true`, `training_finished=true`, `adapter_reload=PASS`, `error` absent.
- **7 optimizer steps**, consistent with 49 samples and gradient accumulation 8; full trainer-state/epoch curve not independently inspected in this audit.
- Final recorded **train_loss=1.9259772300720215**, **validation_loss=1.7483125925064087**, both finite.
- Runner elapsed **1,260.88 seconds** (~21 minutes). This is not a measured billing total or guaranteed whole-Job duration.
- Adapter checkpoint (reported by run): `hf://buckets/adradar/storyforge-training/experiments/v02-r46/r46-20261014T070529Z-248172/output/v0-20261014-070817/checkpoint-7/`.
- `adapter_model.safetensors` SHA256 **as reported by the remote Runner**: `bec4ba74d858db3ff117d581478ef9cac41b1ecc7ea2a67523f6db1096addf2b`.
- Post-train adapter reload and one-sample inference **PASS**, based on the report and owner's generation log. Remote checkpoint bytes have **not** been independently downloaded/rehashed by this reviewer.

## Deliberate release boundary

- Engineering result: **PASS**.
- Fresh independent human-authored and sealed Held-out: **0 received**. Owner is preparing it. Do not use exposed v0.1 test or assistant-authored prompts to claim generalization.
- Formal full-canon/world alias signoff: not exhaustively certified. Original R45 49/15 is explicitly a **scoped experimental dataset**, not a complete admission of the other Gold.
- `formal_data_admission=false` is preserved; no general-purpose release approval or proof v0.2 improves on Base or v0.1.
- v0.1 losses (`1.7067/1.6648`) were obtained using **different datasets**. The loss values cannot be compared as head-to-head model quality scores.
- **No new GPU rerun is necessary for engineering acceptance.** Next steps: confirm checkpoint persistence and prepare independent Base/v0.1/v0.2 blind evaluation after Held-out intake.

**Marker:** `R46_ONE_EPOCH_49_15_ENGINEERING_PASS_ADAPTER_RELOAD_PASS__NO_QUALITY_PROMOTION`.
