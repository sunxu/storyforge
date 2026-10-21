# StoryForge R54 — post-R53 GPU SFT preparation (NO SUBMIT)

Date: 2026-10-21 (Asia/Singapore)

**Recorded status:** `R54_GPU_PLAN_READY__R53_31_9_PRIVATE_RELEASE_ACCEPTED__REMOTE_GPU_STAGING_NOT_DONE__GPU_NOT_AUTHORIZED__R50_SEALED`

## Inputs independently byte checked

- The Owner-returned, accepted V4 private-release receipt `R53_RELEASE_RECEIPT.json`: SHA256 `3d8078ee3b4528521b7f67ba1dd7983f0d20bfeb4d7c79e92d9cabe2c6b2e836`.
- 31 formally admitted Train `train.jsonl` expected SHA256 `d0425c54b534307047457d05e6890b50076ad2d23ce9ab3d52f94d1a3db585a7`.
- 9 formally admitted Validation `validation.jsonl` expected SHA256 `b5ea4075419ce02a1340f6ece875068746918ce1d4c6d72ee2f799b3fe58754d`.
- Frozen Stage manifest: `00b8182812d8bbc33eaacede962506ec718c6b987ef82c429f75401c4c107261`.
- R53 actual CPU40 report: `8624c21b6d9fff5e74006bca000c69f0d39870f1fb030c2ff4fb96cc523f1f45`.
- CPU40 owner-machine original intake receipt: `b3bff2625c360aad10d985b42884263a26a72e85e7d1ddc7d0df916b6598381e`.

The private frozen stage was compiled **locally** with the unchanged V4 compiler to reproduce the 31/9 message-only bytes and SHA256s, then read by the new read-only R54 preflight. The original owner-machine final files were **not downloaded/re-read directly** in this assistant runtime. R53 official V4 private release status was already accepted on the Owner-returned receipt in commit `b47d16c`.

## Model, compute, engineering limitation

Keep R46's original optimizer/model-meaningful hyperparameters:

- `Qwen/Qwen3.8-27B@1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0` (pinned revision), `ms-swift==4.5.3`, `transformers==5.16.1`, `bitsandbytes==0.50.2`.
- 4-bit NF4/BF16 QLoRA; LoRA rank64, alpha128, dropout0.05, target all-linear; 16,384 token max; `loss_scale=last_round`; batch1, gradient accumulation8, lr 5e-5, **one epoch**.
- One GPU, `a100-large` (A100 80GiB), with a contemplated **120-minute max** only **if newly authorized**. This preparation has no `hf jobs run` operation and does not reserve hardware, incur GPU charges, or submit remotely.
- For 31 Train and accumulation8, expect only **4** optimizer steps versus R46's **7**, so this is a small-data engineering pilot, not proof of quality gain.
- Existing R46 `eval_steps=3`, `save_steps=3` would produce at least a step-3 check, but may not guarantee a **final step-4 Adapter**. Before actual launch, guarantee auditable final save and adapter reload, or document an explicit change to checkpoint engineering behavior; do not label a step-3 checkpoint as final.
- Start a new LoRA from the pinned base rather than resuming the R46 optimizer state; use a unique R54 private run key, no overwrite.
- Under the HF published `a100-large` price of USD 2.50/h and indicative 2026-10-21 USD/CNY 6.67805, two hours cost about **RMB 33.39** for compute only; this is not a user budget approval and is subject to actual per-minute billing, exchange rates and other charges.

## Training exposure, evaluation and safety

- R53's 31 Train targets include **23** exact R45 target matches (14 historical Train, 9 historical Validation), plus eight not target-matched. The new training dataset is not wholly historically novel.
- R53 Validation has no exact R45 Validation target repeat, yet story 06 appeared in historical R45 Train, so do not claim every validation world is wholly unseen.
- R53 CPU40 real collator checked singleton cases (0 padding); full GPU runtime readiness remains unmeasured. Also all 40 report items recorded ms-swift vs transformers input token-sequence mismatch; training must use pinned native ms-swift template, not assume cross-template equality.
- Keep R50 completely sealed. R55 exposed R47/R48 tasks can be used for **development regression only**, not as new unseen-test evidence. Final blind evaluation, prompt/deployment contract and explicit separate GPU inference authorization remain later gates.
- No model promotion before independently reviewed evaluation.

## Local executable deliverable

The package `StoryForge_R54_GPU_SFT_PREPARATION_NO_SUBMIT_20261021.zip`, SHA256 **`b2624359dc036e9a267d14947eab7fdba4c85258cf4af52d918be252784db50f`** contains:
- `scripts/v03_r54_gpu_readiness.py`: standard-library-only read-only preflight, refuses incorrect/altered 31/9 final-release bytes, CPU report/intake, original formal release receipt, altered config, history supervision or cross-split final target repeats. It writes only a safe receipt.
- `configs/v03_r54_qlora_one_epoch_31_9.yaml`, proposal exact SHA256 `7ca8700064c30cc1242683deb2a2918db84a9a1179a6ffeeb0aa0fd64e1ea003`. Model revision MUST additionally be pinned by the future runner.
- `tests/test_v03_r54_gpu_readiness.py`: **15/15** offline synthetic and adversarial cases PASS.
- `docs/R54_GPU_PREPARATION_NO_SUBMIT_CN.md`, `receipts/R54_GPU_NO_SUBMIT_PREFLIGHT_SAFE.json`, plus member SHA256 manifest.

This no-submit package contains **no original private story messages, candidate samples, R50 test text, credentials or adapter weights**. Its locally emitted safe receipt status: `R54_GPU_PLAN_READY__NO_GPU_AUTHORIZATION__NO_REMOTE_ACTION`. No HF Bucket action or GPU Job was executed.

## Owner's Mac reproduction

```bash
PKG="$HOME/.local/share/storyforge/r54-no-submit"
mkdir -p "$PKG"
unzip -n "$HOME/Downloads/StoryForge_R54_GPU_SFT_PREPARATION_NO_SUBMIT_20261021.zip" -d "$PKG"
cd "$PKG"
python3 -m unittest discover -s tests -p 'test_v03_r54_gpu_readiness.py' -v
ROOT="$HOME/.local/share/storyforge/r53-authorized-release"
python3 scripts/v03_r54_gpu_readiness.py \
  --release-dir "$ROOT/R53_FORMAL_DATA_ONLY_RELEASE_31_9" \
  --cpu-report "$ROOT/evidence/R53_HF_CPU40_AUDIT_REPORT_PRIVATE.json" \
  --cpu-intake "$ROOT/evidence/R53_CPU40_OWNER_INTAKE_VERIFIED.json" \
  --config configs/v03_r54_qlora_one_epoch_31_9.yaml \
  --out "$HOME/.local/share/storyforge/r54_gpu_readiness_safe.json"
```

Expected: `R54_GPU_PLANNING_PREFLIGHT_PASS__NO_GPU_JOB__NO_R50`.

**Next actual project task is to implement and test the separate R54 GPU worker, unique private sync/submit gates, and final checkpoint/reload validation.** That has NOT been performed here. Actual GPU billing/training requires new and explicit Owner authorization. V4 private data admission does not imply GPU authorization.
