# StoryForge R53 — R45/R46 exposure replay and true CPU label-mask audit handoff

Date: 2026-10-21 (Asia/Singapore)

**Status:** `R45_R46_REPORTED_INPUT_HASH_REPRODUCED__PRIMARY_REMOTE_FILES_PENDING__REAL_QWEN_SWIFT_AUDIT_PENDING__NO_ADMISSION__NO_GPU`

## Reproduced historical data identities

- Original **R45 49 Train / 15 Validation** source ZIP was byte-pinned and the R46-compatible `prepare_sft.py` projection reproduced the **exact two SHA256s quoted in the saved R46 report**:
  - Train compiled SHA256: `a028bf9fb28b12b4a3fa352d6a60281bd9e1ef5773ebfdfecc7ac80eb2cba517`
  - Validation compiled SHA256: `cc8d647471423f4969149f8cabdea980aad15d8bd4424d9dd98da3313c639f3c`
- The **R46 locally archived summary**, SHA256 `4ad35faedc97724f588914f59d3a00293e681e2245d2d74c27d528e3179a8e83`, states A100 80GB GPU exploratory training, **seven optimizer steps**, adapter reloaded, and no formal approval. **We did not read authenticated remote trainer data files, original Job logs or trainer_state.json this turn.** Report consistency does not independently prove actual per-case SGD gradients.
- In current R53 staged **31 Train**, **14** have exact target hashes in R45 Train, **9** in R45 Validation, **8** no exact R45 target match. Among the **23 exact target repeats**, only **5 full role/content `messages` sequences** are identical, while **18 have different historical visible inputs**. R45 Validation entries must not be automatically described as examples receiving optimizer updates.
- All **9 R53 staged Validation** have **no exact target** matches in R45 49/15. However two cases share **story rank 06** with **one R45 Train case**. Their frozen historical message bodies have **zero exact SHA256 overlaps** with that case, which **does not** establish model-unseen world validity.
- Original R53 31/9 stage, Owner-approved source-bounded Reviewer E seven-world policy, six excluded HOLD, sealed R50 and separate paid GPU gate remain **unchanged**.

## Reproducible next steps, not claimed to have run

Private handoff `StoryForge_R53_R45_R46_EXPOSURE_CPU40_AUDIT_PRIVATE_20261021.zip` includes:
- SHA256 `c630d1cf45172834bbecabc91948645b83ae28dd7a09aba0f9a8b74ecc64ef6d`
- **19 archive members**, manifest-verified, and **8/8 fresh-extract negative/source tests PASS**.
- Original private R45 archive, original R46 local report, unchanged staged 31/9 source JSONLs and world certificate, per-case privacy-restricted target/source-overlap comparison; **do not publish the ZIP in Git**.
- A **read-only HF Bucket fetch** script to obtain seven original R46 trainer/input/log/state files from existing run key `r46-20261014T070529Z-248172`. Nothing was fetched remotely here.
- A fail-closed exact-byte validator that can issue the historical primary-input evidence only **after** those seven actual remote files are supplied and checked.
- An executable CPU-only 31+9 audit runner requiring `ms-swift==4.5.3`, `transformers==5.16.1`, the exact `Qwen/Qwen3.8-27B` revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0` locally, and the original `scripts/hf_label_mask_audit.py` pinned Git blob SHA-1 `15296f1d8438f40d727c84913ac658cf6de01cb4`. It writes a REAL PASS receipt only after all 40 actual token-encode / loss masks pass. It does not download weights or run GPU.

**Environment reality:** This execution environment lacked `ms-swift`, `transformers` and the pinned tokenizer snapshot, so **no true tokenizer/collator/label-mask audit was performed**; the fail-closed runner exited **2** on missing code/runtime and produced **no fake PASS**. No paid HF CPU or GPU run launched.

## Remaining release boundaries

- Historical **actual remote** R46 trainer source and optimizer evidence need an authenticated read-only Bucket export to substantiate the local report.
- Full **40/40 actual** pinned Qwen/ms-swift last-round label-mask audit pending.
- Existing separate seven-story rights/provenance **policy** gate remains unresolved; the Owner's original authorship and training-rights attestations are recorded, **not false third-party confirmations**.
- Final dataset release requires an explicitly separate Owner approval bound to exact stage hashes; no such permission is inferred from “continue.”
- Formal Train **0** / Val **0**, R50 still sealed, new paid GPU **not authorized**.

No original story content or private candidate identifiers were added to this Git document.
