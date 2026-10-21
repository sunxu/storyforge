# StoryForge R54 — optimizer cadence and checkpoint V2 contract (NO GPU)

Date: 2026-10-21, Asia/Singapore.

**Status:** `R54_31_9_SCHEDULE_V2_READINESS_PASS__16_EXPECTED_UPDATES__GPU_NOT_AUTHORIZED__R50_SEALED`

## Explicit Owner request

Owner requested adjusting the planned R54 optimizer step count to a more practical value and replacing the legacy R46 save-every-3-updates strategy. This authorization is for **configuration engineering only**; it does **not** authorize a GPU Job, training, or touching R50. Previous R46 checkpoint and original R54 V1 plan remain immutable.

## Versioned optimizer and checkpoint contract

Exact new config: `configs/v03_r54_qlora_31_9_16step_v2.yaml`, SHA256 `55ac554a4fe4b4974b7f7f664dcf5a9163b5e37219150acc087309282ef4d861`, Git blob `b9fad0f9f1152072ec2977eb402eef50887e8ab5`.

| Setting | R54 V1 proposal | R54 V2 selected |
|---|---|---|
| Train/Validation count | 31/9 | **31/9 unchanged** |
| Training epochs | 1 | **1 unchanged** |
| Train microbatch per GPU | 1 | **1 unchanged** |
| Gradient accumulation | 8 | **2** |
| Effective batch size (one GPU) | 8 | **2** |
| Expected optimizer steps | 4 | **16** (`ceil(31/2)`) |
| Evaluation every | 3 updates | **4 updates** |
| Checkpoint save every | 3 updates | **8 updates** |
| Retained checkpoints maximum | 2 | **3** |
| Automatic load best | implicit false | **explicit false** |

Expected validation checkpoints: steps **4, 8, 12, 16**; periodic save steps **8, 16**. Actual `global_step` must be verified after runtime completion; do not claim 16 steps merely because the plan computes 16. The future runner must enforce a final `checkpoint-16/` containing **trainer_state.json + adapter_model.safetensors + adapter_config.json**, and a separately checked adapter reload/inference receipt. If framework ends without a real final checkpoint, fail closed and diagnose rather than relabel step 8 as final. `load_best_model_at_end=false` avoids treating a nine-case development validation minimum as an automatically promoted checkpoint; future independent review controls promotion.

All other R46 model-critical settings are preserved (pinned Qwen3.8-27B revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`, QLoRA 4-bit NF4/BF16, LoRA rank64/alpha128/dropout .05, last-round loss only, LR 5e-5, length 16384). **The accumulation factor changes optimization dynamics, so R54 versus R46 is no longer a pure dataset-only ablation**, even though sample exposure remains exactly one epoch. Do not claim improved model quality from more steps alone.

## Actual completed safe checks

- Re-executed new V2 strict read-only preflight against the locally reconstructed, frozen Owner-released **31 Train / 9 Validation** message-only bytes; exact source checks and CPU report/intake hashes passed. Original Mac-owned final training files were **not** re-read directly here.
- Original R53 freeze manifest SHA256 `00b8182812d8bbc33eaacede962506ec718c6b987ef82c429f75401c4c107261` unchanged; released Train hash `d0425c54b534307047457d05e6890b50076ad2d23ce9ab3d52f94d1a3db585a7`, Validation `b5ea4075419ce02a1340f6ece875068746918ce1d4c6d72ee2f799b3fe58754d`, all unchanged.
- No-runtime V2 readiness tests **15/15 PASS**; final-checkpoint/adversarial reload test suite **12/12 PASS**, total **27/27 PASS**, replayed from a freshly unzipped package.
- Original read-only V1 preflight and configuration remain historical reference. No remote HF sync, paid GPU, SFT, weight export, or model inference was performed in this action.
- The final checkpoint gate `scripts/v03_r54_last_step_checkpoint_gate.py` and its 12 synthetic tests are in main. Test successes are **not** evidence that a genuine checkpoint or adapter reload already exists.

## Portable deliverables

No-private-narrative ZIP `StoryForge_R54_16_UPDATE_CHECKPOINT_SCHEDULE_V2_NO_GPU_20261021.zip` SHA256 `9f7b418cc63b27d463656d0a7f8c3d8bdf68f43deb10dddd4e9d703152e1b7bb` containing:
- immutable V2 config;
- strict R53 frozen-data + CPU-evidence-readiness preflight `scripts/v03_r54_gpu_readiness_v2.py`;
- fail-closed step-16 + adapter reload evidence check;
- 27 offline tests, Chinese instructions, safe aggregate real-source replay receipt, SHA256 manifest.
- ZIP and verified receipt are stored in the conversation workspace; the packaged original story text, candidate IDs, secrets and R50 data are **absent**.

Safe no-GPU receipt: `R54_SCHEDULE_V2_SAFE_RECEIPT_20261021.json`, SHA256 `116fb16563b540569ef2da19d62ec54d967f37fe1d068dde53d18cd79ad28b9c`.

## Next step

Build a separate, auditable R54 HF GPU Worker + `sync → submit → verify` pipeline pinned to this V2 config and the exact 31/9 private-release bytes. Guarantee a complete last-step checkpoint and real adapter reload **before** any PASS result. Actual GPU Job may begin only under a **new, express Owner paid-GPU permission** with budget and unique run key. R50 remains sealed.
