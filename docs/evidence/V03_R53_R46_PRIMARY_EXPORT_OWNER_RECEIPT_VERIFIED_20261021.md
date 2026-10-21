# StoryForge R53 — Owner-uploaded R46 primary-export verification receipt cross-checked

Date: 2026-10-21. Status: `R46_PRIMARY_EXPORT_OWNER_MACHINE_RECEIPT_ACCEPTED__R45_BYTES_REPRODUCED__CASE_GRADIENT_NOT_PROVEN__NO_DATA_RELEASE`.

## Artifact received

The owner uploaded `R53_R46_PRIMARY_INPUT_EVIDENCE_VERIFIED_PRIVATE.json` (2,075 UTF-8 bytes), SHA256 `e340aff32fde5dc326070b84f300783749ade4c80135f6ac1313db17c152cf5e`.

The uploader says its local authenticated, read-only Hugging Face Bucket export of **seven original R46 files** was validated by the corrected `r53_verify_r46_primary_export.py` and issued status `R45_R46_RUNTIME_INPUT_EXPOSURE_RECONCILED_WITH_PRIMARY_ARTIFACTS`. The verifier captures trainer `commands.log` and `trainer_state.json`, and cross-checks exact dataset input files with the frozen R45 source.

## New local independent cross-check of receipt against frozen artifacts

Recomputed in this environment, without accessing R50:

- Original R45 source ZIP SHA256 `da4b7718f1c1cbd0429553b684eeaf70f207fd2e41aae4e8fe0a52a11b647b9e`, 49 frozen Train / 15 frozen Validation, passed.
- Local archived R46 training report SHA256 `4ad35faedc97724f588914f59d3a00293e681e2245d2d74c27d528e3179a8e83`, exactly matches uploaded remote-export receipt declaration including 2069-byte file length.
- The R45 frozen source-data byte streams equal the input SHA256 and sizes recorded for `source-data/train.jsonl` and `source-data/validation.jsonl` in the uploaded receipt.
- The official R46 `prepare_sft.py` equivalent exact-byte compiler independently generated `train.jsonl` SHA256 `a028bf9fb28b12b4a3fa352d6a60281bd9e1ef5773ebfdfecc7ac80eb2cba517`, and `validation.jsonl` SHA256 `cc8d647471423f4969149f8cabdea980aad15d8bd4424d9dd98da3313c639f3c`, with exact lengths **391988** and **151854** bytes. Both agree with the uploaded receipt and R46 report.
- Current staged R53 dataset manifest and 31 Train / 9 Validation staged source bytes are unchanged.
- R46 owner-machine receipt names the correct run key `r46-20261014T070529Z-248172` and 7 trainer optimizer steps.

The uploaded receipt also lists exact SHA256 and byte lengths for `commands.log` and `checkpoint-7/trainer_state.json`; their syntax and presence in the receipt were verified. **However, the actual seven exported remote files were NOT attached or independently reread within this conversation/container.** Their reported checksums and trainer-state contents cannot be independently rehashed here. Accept as a user-machine generated primary-source verification *receipt*, not a second local full remote-file attestation or independently signed third-party proof.

## Interpretation

- R53 31 staged Train contains **14** exact R45 Train target repeats and **9** exact R45 Validation target repeats; **8** with no exact R45 target. Validation contains 9 without exact R45 target, with known same-world (story rank 06) overlap.
- A reported 7 optimizer steps and dataset membership do **not** prove per-case gradient updates. R45 Validation is not reclassified as trained cases.
- Previous R46 experimental adapter was not formally promoted.
- Pending hard gates: actual Qwen3.8-27B pinned revision / ms-swift 4.5.3 **full 40/40 CPU label-mask** with authentic logs; separately defined rights/provenance policy and exact-byte formal dataset-release approval. Paid GPU remains unauthorized, formal Train/Val **0/0**, R50 sealed.

Independent local machine-readable aggregate cross-check: `R53_R46_PRIMARY_EXPORT_UPLOADED_RECEIPT_CROSSCHECK_SAFE_20261021.json` (conversation attachment; private status evidence stays outside Git).
