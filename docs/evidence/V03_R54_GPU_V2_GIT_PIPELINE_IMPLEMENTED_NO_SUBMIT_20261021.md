# StoryForge R54 V2 — GPU pipeline implementation (NO SUBMIT)

Date: 2026-10-21, Asia/Singapore.

**Recorded status:** `R54_GPU_SYNC_SUBMIT_VERIFY_CODE_READY__EXACT_31_9_PINNED__PAID_GPU_NOT_AUTHORIZED__R50_SEALED`.

## Actual work

The following code was committed to `main` and fetched back for source checks:

1. `configs/v03_r54_qlora_31_9_16step_v2.yaml` — frozen config SHA256 `55ac554a4fe4b4974b7f7f664dcf5a9163b5e37219150acc087309282ef4d861`.
2. `scripts/v03_r54_gpu_readiness_v2.py` — Git-native version of exact R53 31/9 private-release and CPU40 evidence preflight.
3. `scripts/v03_r54_gpu_remote_guard.py` — actual HF Bucket object enumeration and exact expected stage list; empty listing exit status is never treated as object existence.
4. `scripts/v03_r54_gpu_submit.sh` — `sync` local authenticated source checks and immutable private Bucket uploads; `submit` two explicit paid approval flags, remote stage check, local idempotency lock and remote submission marker **before** the one `hf jobs run` occurrence.
5. `scripts/v03_r54_gpu_worker.sh` — checks paid run scope and remote SHA256SUMS before dependency or model work.
6. `scripts/v03_r54_gpu_runner.py` — frozen source gate; one A100; pinned ms-swift/transformers/bitsandbytes; real 40/40 label audit; pinned model weights; one epoch `swift sft`; checkpoint-8 and checkpoint-16 with actual step 16; model output reload/inference without Gold target.
7. `scripts/v03_r54_last_step_checkpoint_gate.py` — requires terminal checkpoint global_step 16, all four scheduled validation points 4/8/12/16, LoRA adapter bytes and configuration; authentic runner reload evidence must match saved adapter SHA.
8. `scripts/v03_r54_gpu_verify.py` — later owner-provided GPU report/runtime log/reload receipt exact-source checks and explicit **no independent weight rehash** limitation.
9. `tests/test_v03_r54_gpu_pipeline.py` — **25** network-free positive, negative, and static-safety test cases (written, **not executed in this assistant container**).
10. `docs/V03_R54_HF_GPU_V2_SYNC_SUBMIT_VERIFY_CN.md` — fully reproducible Mac commands and scope notes.

The original proven label auditor `scripts/hf_label_mask_audit.py` must match the old R53 audited Git blob SHA1 `15296f1d8438f40d727c84913ac658cf6de01cb4`. The worker won't transform the formal R53 training bytes, and original data-only approval **does not** confer new GPU permission. Original R46 and R53 records are immutable.

## Checks actually run

- Original V2 no-paid data preflight and final checkpoint synthetic test suites were replayed locally: **27/27 PASS**. These tests predate the new R54 GPU workflow and must not be mistaken for an on-GPU test.
- **15/15** cross-file GitHub source invariants checked against **freshly fetched** `main` files (config cadence, 31/9 pins, original auditor pin, submit authorization gates, remote mark, stage completeness, checkpoint/reload and success marker).
- **25 new network-free GPU pipeline test cases are present but have NOT been executed in this environment.** No new source syntax, CUDA, A100 memory, HF CLI integration or actual model reload was certified here.
- The user can run those tests safely after `git pull`; any failure is BLOCKED and should be corrected before staging or launching.

## Exact one-time runtime scope (future authorization only)

- Base `Qwen/Qwen3.8-27B@1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`.
- Formal Train 31 SHA256 `d0425c54b534307047457d05e6890b50076ad2d23ce9ab3d52f94d1a3db585a7`; Validation 9 SHA256 `b5ea4075419ce02a1340f6ece875068746918ce1d4c6d72ee2f799b3fe58754d`.
- 1 epoch; accum2, batch1; expected 16 optimizer steps; validation on steps 4/8/12/16; save 8/16; final adapter reload mandatory. Since R46 used accumulation8 and save3, this is **not** a dataset-only A/B comparison.
- One future `a100-large`, 120m hard timeout **only after a separate explicit paid GPU authorization**. User's current `继续` is not paid authorization.
- The newest run must use a unique `r54-v2-...` key, never overwrite or resume R46. The remote submission marker reduces accidental repeat billing but is not a formally atomic distributed lock across independent terminals. If submission status is uncertain, **do not retry automatically**.

## Status and next action

Actual R54 HF `sync`, `submit`, runtime training, Adapter Reload and result verification have **NOT been performed here**; there is no current R54 Job ID and no R54 checkpoint to accept.

Next safe user action: update Mac Git checkout and run `python3 -m unittest discover -s tests -p 'test_v03_r54_gpu_pipeline.py' -v`; if PASS, use **sync only** to stage the already released private R53 files in the existing HF private Bucket. Save the emitted `R54_RUN_KEY`, return its metadata. **Do not submit GPU until the Owner separately approves single-job scope/cost.**

Source detail and runnable commands: `docs/V03_R54_HF_GPU_V2_SYNC_SUBMIT_VERIFY_CN.md`.
