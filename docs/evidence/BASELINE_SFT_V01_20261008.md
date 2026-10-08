# StoryForge Baseline SFT v0.1 — Engineering Acceptance

**Status: PASS — CLOSED (engineering), MODEL QUALITY UNVERIFIED.**

## Run identity
- HF Job: `6ac75bafdf2184ac91acb293`
- Git baseline: `35cb49e82f53a8931f765eb93aa9b8fcca3df9a6`
- Base model: `Qwen/Qwen3.8-27B`
- Dataset: v0.3, 65 train, 15 validation, 20 held-out test
- Config: `configs/qwen38-27b-qlora-v0.1.yaml`
- Config SHA256: `8569a7b5502308ae4cd7d6778152ae7dca19303ee486632f6bd89ef6b099fbfa`
- Adapter checkpoint: `hf://buckets/adradar/storyforge-training/baseline-runs/baseline/6ac75bafdf2184ac91acb293/output/v0-20261008-090236/checkpoint-9`

## Verified from user-provided remote summary and success marker
- Final `status: PASS` and `BASELINE_PASS` marker exists.
- Global optimizer steps: **9**
- Final train loss: **1.70667564868927**
- Evaluation loss: **1.6648403406143188**
- Sampled peak VRAM: **69013 MiB**
- Wall-clock duration: **3699.7 seconds**
- Data preflight and gold-only label audits: PASS
- Checkpoint weights: `adapter_model.safetensors`
- Adapter reload and generation: PASS as reported by the remote runner

## Preceding rank-64 capacity gate
- HF Job: `6ac74ce3df2184ac91ac8f43`
- `CAPACITY_PASS` present; one optimizer step; peak 56345 MiB
- Config SHA256 equals baseline SHA256

## Limitations
- This is an engineering acceptance. It does **not** establish quality gains over the base model.
- Check `trainer_state.json` `epoch` and full logs before asserting every intended example was consumed.
- The final reported loss is not directly comparable to the earlier rank-32, 3-step smoke.
- Do not tune against the 20 held-out test samples.
- Preserve the adapter and evidence in the HF private Bucket; do not commit the training data or checkpoints to Git.
- Evidence above is drawn from provided HF Job reports, not an independently reproduced run.
