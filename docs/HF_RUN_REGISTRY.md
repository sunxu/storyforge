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

## Base model revision evidence (2026-10-09)

- Model: `Qwen/Qwen3.8-27B`
- Hugging Face current repository revision returned by `HfApi.model_info()`: `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`
- Repository last modified according to HF API: `2026-08-14 15:00:01+00:00`
- Local Mac cached snapshot: `models--Qwen--Qwen3.8-27B/snapshots/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`
- **Training-job-resolved base revision: VERIFIED from the completed baseline HF Job log** (`6ac75bafdf2184ac91acb293`): `[INFO:swift] Loading the model using model_dir: /workspace/cache/huggingface/hub/models--Qwen--Qwen3.8-27B/snapshots/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`. The same snapshot is shown again under `model_info.model_dir` and `lora_config.base_model_name_or_path`. `hub_revision=None` and `model_revision=None` reflect unspecified explicit overrides, not an unknown loaded snapshot.
- Artifact adapter file SHA256: `621d7328056758607c9d7797282ae4d5803cdb1727dab6b40a321ee959dd2478`, reported by completed CPU Job `6ac8be0e095c578089304f37`.

## Baseline checkpoint SHA256 manifest (CPU verification, 2026-10-09)

The following SHA256 checksums were reported by the completed Hugging Face CPU Job `6ac8be0e095c578089304f37`, with terminal marker `STORYFORGE_SHA256_PASS`. They refer to the ten files in the previously accepted baseline `checkpoint-9` directory. This is verification **as reported by the user's remote CPU Job output**; the repository does not store the 5.60 GB checkpoint contents, and these bytes were not independently rehashed by the repository CI.

```text
f800dff428b64eb5f2b32b525ccc5220a222faf721b003f779ae2b2825f7e60a  ./README.md
8e1ea2e3fbdab719ab500664acd87f30ae38d1c107655301198ef318e61cc793  ./adapter_config.json
621d7328056758607c9d7797282ae4d5803cdb1727dab6b40a321ee959dd2478  ./adapter_model.safetensors
c7799462ebedae6557ffad31566029e2d2f958b7b40e46e972cf901bcaf45733  ./additional_config.json
4402231ac5a5c50d149163cf8b37f4eb0feef8a0f42715ea25c7edfcb9d37de8  ./args.json
6c67c93509284f69893b9e024cccb6a3ad5a299bf0cec2a29789f13a773521f6  ./optimizer.pt
e7d7f29b8b92e06b42a8166ade972e2162c7ccb0e0abeb9d93b8f09937b34df0  ./rng_state.pth
566db558936da179408fc6d7c6a556419a6eb8889df0820b89ada4047b190ffb  ./scheduler.pt
b6c03601d9a63cb998b67b8443399ccfc5c6b00f6d3a8c4135716f784f626c8a  ./trainer_state.json
f649fa91bdc10620b030801b8c5def77c26ecdd1c857be9d6bcb8f62f8d74678  ./training_args.bin
```

The manifest may be used for future integrity checks; if the source bucket changes, rerun hash validation and compare against this frozen reference.

### Checkpoint byte-size metadata (HF Bucket listing, 2026-10-09)

**Status:** `SIZE_METADATA_PASS__SHA256_REPORTED_BY_PRIOR_CPU_JOB`.

The authenticated read-only HF Bucket query via `HfFileSystem.ls(detail=True, refresh=True)` reported ten files at the canonical `checkpoint-9` directory, collected **2026-10-09T11:08:34.241484+00:00**. All ten filenames match the previously recorded CPU Job hash manifest exactly, and the supplied `size_bytes` values sum to **5,603,977,212 bytes** (approximately **5.604 GB**, decimal).

Machine-readable evidence: [`docs/evidence/V01_CHECKPOINT_SIZE_MANIFEST_20261009.json`](evidence/V01_CHECKPOINT_SIZE_MANIFEST_20261009.json), preserving the source Checkpoint URI, HF Job ID, hashes, exact byte sizes, source and query time.

| Checkpoint filename | Size (bytes) |
|---|---:|
| `README.md` | 5,372 |
| `adapter_config.json` | 1,282 |
| `adapter_model.safetensors` | 1,867,797,544 |
| `additional_config.json` | 67 |
| `args.json` | 18,432 |
| `optimizer.pt` | 3,736,129,330 |
| `rng_state.pth` | 14,244 |
| `scheduler.pt` | 1,000 |
| `trainer_state.json` | 3,549 |
| `training_args.bin` | 6,392 |
| **Total (10 files)** | **5,603,977,212** |

**Evidence distinction:** the *size metadata* was collected from the HF Bucket listing and independently checked for internal consistency against the previously reported ten files; the SHA256 values were computed in the **earlier CPU Job** `6ac8be0e095c578089304f37` (terminal marker `STORYFORGE_SHA256_PASS`) and were copied from this registry by the metadata-only script. The size query **did not rehash payload bytes**. The repository CI also did not rehash the remote 5.60 GB payload. No new HF Job, GPU instance, checkpoint download, or Bucket write is required.

To reproduce the metadata listing with an authorized HF account:

~~~bash
python3 -m pip install -U huggingface_hub
hf auth whoami
python3 scripts/hf_checkpoint_size_manifest.py \
  --output /tmp/storyforge-v01-checkpoint-sizes.json
~~~

The script rejects missing/unexpected file names and invalid sizes; it does not open or mutate Checkpoint files or overwrite an existing local report.

## Reproducibility metadata still pending

The checkpoint hashes below are now recorded from completed CPU Job output; other unresolved provenance remains explicitly marked:

| Field | Status | How to obtain |
|---|---|---|
| Exact **training-job-resolved** base model HF revision / commit SHA | VERIFIED: `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0` | Baseline HF Job `6ac75bafdf2184ac91acb293` log, `model_dir` and `lora_config.base_model_name_or_path` |
| `adapter_model.safetensors` SHA256 | REPORTED VERIFIED: `621d7328056758607c9d7797282ae4d5803cdb1727dab6b40a321ee959dd2478` | CPU Job `6ac8be0e095c578089304f37`, `STORYFORGE_SHA256_PASS` |
| Checkpoint accompanying file SHA256 values | REPORTED VERIFIED: 9 additional files listed above | CPU Job `6ac8be0e095c578089304f37`; no tokenizer file present in the reported checkpoint listing |
| Exact byte sizes for all 10 Checkpoint files | SIZE_METADATA_PASS: total 5,603,977,212 bytes | Authenticated HF Bucket file listing at 2026-10-09 11:08:34 UTC; [machine-readable evidence](evidence/V01_CHECKPOINT_SIZE_MANIFEST_20261009.json); metadata only, no rehash |
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
