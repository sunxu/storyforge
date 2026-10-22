# StoryForge R55 — Owner-authorized single paid development inference, code prepared

Date: 2026-10-22 (Asia/Singapore).

**Current status:** `R55_ONE_PAID_DEV20_INFERENCE_OWNER_AUTHORIZED__OFFLINE_26_TESTS_PASS__REMOTE_NOT_STAGED__GPU_JOB_NOT_SUBMITTED__R50_SEALED`.

## Explicit scope

The Owner explicitly replied **“授权”** to a request for a **single billable R55 GPU inference** using the **same already exposed 20 R47/R48 development prompts** and the existing **R54 Step-16 Adapter**. Authorization **excludes** training, automatic retries, touching sealed R50, and model promotion. This is distinct from the old R54 training authorization. The concrete executor uses **one HF `a100-large` A100 80GB with a 120-minute hard timeout**, with no auto-retry. The 120m maximum is an engineering cap, not a claimed actual runtime or bill.

## Pinned sources and inference

- Original 20 prompts Git blob SHA1: `ac301a61d4130369a83dc67ac02aa2d8dda9e82b`.
- Original 20-manifest Git blob SHA1: `f4e39196c6aa0a87b095d7de5cae4acd8b2fca63`.
- R46 20 responses from existing verified R47 run `r47-20261014T091647Z-637890`: **not** regenerated.
- R54 training run: `r54-v2-20261021T161818Z-507469`.
- R54 `checkpoint-16` adapter expected SHA256 `121ec8f70e66089c7c891a7052c6085de93824776aaa9a25295f612b269b60c0`. Actual adapter weight bytes must be SHA256-verified on GPU before inference.
- Frozen Qwen base `Qwen/Qwen3.8-27B@1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`.
- `temperature=0`, `seed=42`, `data_seed=42`, `max_new_tokens=1536`, `val_dataset_shuffle=false`. All original full user/system history must align with output, exactly 20/20. The R54 single Validation reload smoke result is not a substitute.

## Code deliverable and verified offline checks

The private source-free handoff archive `StoryForge_R55_Single_Authorized_Inference_20261022.zip` is pinned by SHA256 `8f3ff4fd4491d86c4c4456563bf58546407c1058ae300afb9adc802bc5280353` (18,062 bytes; **9 files**; ZIP CRC and packaged SHA256 manifest verified).

The ZIP contains only executable scripts, one inference scope contract, synthetic offline tests and instructions, **no narrative prompt bytes, model replies, adapter weights, credentials, or R50 material**:
- `scripts/r55_gpu_infer_runner.py`: exact original 20 prompts + R54 Adapter and model revision gates, real GPU and dependency checks, one `swift infer`, strict output-alignment check, private generation report.
- `scripts/r55_gpu_infer_worker.sh`: scope guard and all staged files' SHA256 verification before executing the runner.
- `scripts/r55_gpu_remote_guard.py`: fail-closed HF Bucket object enumeration; refuse reused, partial, unexpected or previously submitted runs.
- `scripts/r55_gpu_infer_submit.sh`: `sync` private files without GPU, then separate Owner-scoped `submit` with full remote-v-local source pin checks, local and HF submission markers before the **single** `hf jobs run`; no automatic retry.
- `scripts/r55_gpu_infer_verify.py`: CPU-only Owner-side completed 20/20 response verification against original R47 prompt source and report digest, before any anonymous reviews.
- `tests/test_r55_gpu_inference_pipeline.py`: **26/26** network-free synthetic/offline tests **executed PASS**, including source, adapter, 20-prompt scope and anti-repeat gates.
- `docs/README_R55_SINGLE_PAID_INFERENCE_CN.md`: exact local commands for Mac `sync → submit → verify` and later blind review.
- `configs/r55_dev_infer_contract.json`; `SHA256SUMS.json`.

Safe status receipt `R55_SINGLE_GPU_INFERENCE_OWNER_AUTHORIZED_SAFE_RECEIPT_20261022.json` SHA256 `d4358d40765f4d0532b2a8259f6f3bc95643b96aba6d7f385d935d0f43c052d6`.

**The executable code and tests are delivered in the ZIP, not individually committed to GitHub in this turn.** The original 20 prompts and R47 validator are taken by the Mac sync script from the user's existing Git checkout. The GitHub record is a safe, aggregate-only reproducibility index, not a code-commit claim.

## Strict status and follow-up

No HF Bucket R55 sync, paid R55 GPU Job, 20 R54 development responses, scored CSV or new blind-review result was actually generated in this assistant execution. The user's explicit authorization has been recorded; the next owner-side action is to **test the package, sync a NEW `r55-dev-...` run key and invoke the single guarded paid submit once**, then preserve the actual HF Job ID and new output hashes. Never treat the old R54 training Job or exposed R47 comparison as new R55 inference.

Even a successful R55 20-case review is **development regression only**. The **same 20 exposed prompts** were reused across R47 and R48, across two historically exposed story worlds. No R50 read or model quality promotion permitted.
