# StoryForge Hugging Face Run Registry

**Updated:** 2026-10-09  
**Status:** v0.1 completed; engineering PASS, quality promotion NOT APPROVED.

This is a navigation and provenance index for the frozen v0.1 research cycle. The authoritative historical record is Git tag `v0.1-evidence-frozen` at commit `d1186a731a81219f86eb81b89ac1440dd116e9f4`. This index was added **after** the tag; do not move or rewrite that tag.

## Identity and storage

- HF organization: `adradar`
- Base model: `Qwen/Qwen3.8-27B`
- Artifact bucket: `hf://buckets/adradar/storyforge-training`
- Dataset: v0.3, 65 train / 15 validation / 20 story-held-out test
- Baseline training config: `configs/qwen38-27b-qlora-v0.1.yaml`
- Accepted baseline config SHA256: `8569a7b5502308ae4cd7d6778152ae7dca19303ee486632f6bd89ef6b099fbfa`

## Job index

| Stage | HF Job ID | Status / evidence | Output |
|---|---|---|---|
| Rank32 smoke, 3 optimizer steps | `6ac73cabe7a0dae8a278117a` | PASS; `docs/evidence/GPU_SMOKE_20261008.md` | `runs/6ac73cabe7a0dae8a278117a/output/v0-20261008-065009/checkpoint-3` |
| Rank64 single-step capacity gate | `6ac74ce3df2184ac91ac8f43` | PASS; `docs/evidence/BASELINE_SFT_V01_20261008.md` | See remote Job |
| Rank64 baseline, one epoch | `6ac75bafdf2184ac91acb293` | PASS, 9 steps; baseline acceptance document | `baseline-runs/baseline/6ac75bafdf2184ac91acb293/output/v0-20261008-090236/checkpoint-9` |
| Validation paired evaluation (15 prompts) | `6ac794fae7a0dae8a2788ee6` | PASS; validation reviewed separately | See remote Job |
| Held-out paired evaluation (20 prompts) | `6ac85c22fee2c90070172dad` | PASS; two independent review rounds and arbitration | `evaluation-runs/test/6ac85c22fee2c90070172dad/` |

**Path rule:** relative output paths in the table are below `hf://buckets/adradar/storyforge-training/`. A Job ID and path are provenance references, not a guarantee that the remote object is still accessible.

## Accepted baseline training result

- Source Git commit: `35cb49e82f53a8931f765eb93aa9b8fcca3df9a6`
- Base: `Qwen/Qwen3.8-27B`; QLoRA rank64, BNB NF4 4-bit / BF16, `max_length=16384`
- Train loss: `1.70667564868927`
- Evaluation loss: `1.6648403406143188`
- Sampled peak VRAM: `69013 MiB`
- Elapsed: `3699.7 s`
- Adapter reload/inference: PASS per accepted job evidence
- Canonical Adapter path: `hf://buckets/adradar/storyforge-training/baseline-runs/baseline/6ac75bafdf2184ac91acb293/output/v0-20261008-090236/checkpoint-9`

## Reproducibility metadata still pending

These values **have not been independently verified** and should not be guessed:

| Field | Status | How to obtain |
|---|---|---|
| Exact base model HF revision / commit SHA | PENDING | Record resolved snapshot revision from the completed Job manifest or base model cache metadata |
| `adapter_model.safetensors` SHA256 | PENDING | Hash the existing checkpoint file from the saved HF Bucket; do not rerun training |
| Adapter config/tokenizer file checksums | PENDING | Hash files present in the saved checkpoint; record exact file names and hashes |
| Validation inference config/prompts hashes | PARTIALLY RECORDED | Cross-reference frozen validation evidence before claiming exact source-file equality |

**Note:** The baseline Job is `6ac75bafdf2184ac91acb293`; the different rank64 capacity Job is `6ac74ce3df2184ac91ac8f43`. Do not confuse their artifacts.

## Evaluation and quality disposition

- Frozen test generation: 1536 new tokens, temperature 0, seed 42, data_seed 42, no shuffle
- First round (4 reviewers + arbitration): Base wins 13 / Adapter wins 7
- Second round (3 reviewers + arbitration): Base wins 10 / Adapter wins 10
- Second-round raw votes: Base 34 / Adapter 25 / tie 1
- Second-round quality dimensions: Base overall 3.0067 / Adapter overall 2.8367
- The second round used corrected `ceh-fixed.csv`; the original ceh and the two different `ch.csv` reviewer files are preserved by round
- Source evidence: `evaluations/v0.1/`, including original test key and both review rounds
- Decision: `ENGINEERING_PASS / QUALITY_PROMOTION_NOT_APPROVED`

The 20-item held-out test is now a **retrospective analyzed benchmark**, not an untouched future acceptance set. Do not tune a successor against it and claim independent generalization.

## Access and credentials

The user authorized public archiving of v0.1 story/evaluation evidence. Never commit actual HF tokens, GitHub credentials, private SSH keys, or environment secrets. Model weights and large checkpoints remain in HF storage. No remote GPU Job is required to update this registry.
