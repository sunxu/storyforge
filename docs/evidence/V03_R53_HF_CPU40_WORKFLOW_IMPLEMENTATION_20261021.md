# StoryForge R53 — Hugging Face CPU40 workflow implementation

Date: 2026-10-21.

**Status:** `R53_HF_CPU40_CODE_COMMITTED__STATIC_STAGE_31_9_PASS__REAL_RUNTIME_NOT_RUN__NO_DATA_RELEASE__NO_GPU`.

A Git-native `sync → submit → verify` workflow is now committed under `scripts/v03_r53_hf_cpu40_*` on `main`, with `tests/test_v03_r53_hf_cpu40.py` and operator guide `docs/V03_R53_HF_CPU40_SUBMIT_VERIFY_CN.md`. Uploaded GitHub blobs were compared to the offline-tested local source bytes and matched exactly.

## Scope and controls

- **Source:** 31 provisional Train and 9 provisional Validation **NOT_ADMITTED** rows, original story inputs and final targets unchanged.
- Frozen source SHA256: Train `f17fc33f566b5a1ddd424de2d26a032a812453255c76e0f5fa321fb0f3a9ecf9`; Validation `83e3d1ab4cc955c4b5bba2afc63f355a227934a89203bcc058cfb922a093b01d`; manifest `00b8182812d8bbc33eaacede962506ec718c6b987ef82c429f75401c4c107261`.
- Worker checks the exact uploaded source/code SHA256 and R53 frozen input/target/historical message bytes **before pip install**. Historical Git-blob-pinned `scripts/hf_label_mask_audit.py` is unchanged.
- `sync` uploads only to the owner's existing private HF Bucket and **does not launch Jobs**.
- `submit` requires BOTH explicit `STORYFORGE_ALLOW_PAID_CPU=YES` and `STORYFORGE_R53_CPU40_NO_TRAIN_ONLY=YES`; uses `cpu-upgrade` and a maximum timeout of 120m. **No submit occurred in this task.**
- Runtime job is pinned to `ms-swift==4.5.3`, `transformers==5.16.1`, tokenizer-only `Qwen/Qwen3.8-27B@1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`. It tests real transformers tokenization, template last-round target mask, real Collator, Padding, per-row label digests and all 40 cases without `swift sft`, GPU or R50 access.
- Owner-local read-only `verify` compares the returned report, original frozen IDs and SHA256, claimed runtime versions, original log and per-case 40/40 counts; a valid return **does not itself authorize Train/Validation release**.

## Actual offline checks performed

- Frozen 31/9 stage preflight: **PASS**, with compiled message-only SHA256 matching the earlier R53 stage.
- Pure-Python source, target, mask-structure and Collator edge-case regression: **12/12 PASS**.
- `bash -n` and Python source compilation: PASS.
- No real HF Job was created, no actual Qwen/ms-swift runtime mask result produced, no paid CPU or GPU resources invoked.

Private audit/deployment handoff (conversation only, not Git):
`StoryForge_R53_HF_CPU40_SYNC_SUBMIT_VERIFY_PRIVATE_20261021.zip`

ZIP SHA256: `2cb9c88f71ccf552a68dfd58d2bf76597b7b2d5aa7d07907f0d69b86db861120`. Contains 12 verified entries including private source text. Never commit the archive or private stage to Git.

**Remaining independent gates:** actual 40/40 HF CPU runtime verification, rights/provenance release policy, exact-byte dataset release authorization. R46 primary export owner-machine receipt already cross-checked. Formal Train/Val admitted **0/0**, R50 sealed, GPU not authorized.
