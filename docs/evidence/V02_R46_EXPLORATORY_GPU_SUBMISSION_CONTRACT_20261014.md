# StoryForge v0.2 — R46 prioritized experimental GPU QLoRA submission contract

Date: 2026-10-14. Status: **GPU LAUNCHER PREPARED / LOCAL SIMULATION PASS / NO REAL HF GPU JOB SUBMITTED BY ASSISTANT**.

## Explicit scope of the owner's new direction
Owner instructs to prioritize GPU training while independent Held-out is being prepared. This supersedes *the earlier requirement that new Held-out must exist before any exploratory GPU compute*, **only for this single provisional pilot**, and does not authorize model promotion, unrestricted follow-up runs or publication. Project owner has already asserted internal story usage rights and legal-age compliance, without documentary upload obligations.

## Exact pinned input and experimental contract
- R45 exact private ZIP SHA256: `da4b7718f1c1cbd0429553b684eeaf70f207fd2e41aae4e8fe0a52a11b647b9e`.
- Train **49** original-line candidate SHA256: `e7442993088617c4eaefd3a0c9efc7651932f7048f34586046bf6d5b5981a742`.
- Validation **15** original-line candidate SHA256: `5ebbb3c6986a5ac4d294175bab1980ee61df08536f9b8438c8a67010630f1963`.
- Original Gold195 unchanged. Eighteen experimental exclusions from R39's frozen 82 remain excluded. The source metadata still says `dataset_admission=NOT_APPROVED`; this is not rewritten, and the experiment-specific approval is recorded separately in job environment.
- Legacy CPU actual Collator result for the immutable 64 source rows inherited from R43; **the R46 runner repeats a full actual compiled-data target-only label-mask audit before SFT starts**, because `prepare_sft.py` creates a minimal-schema derivative.
- Model: `Qwen/Qwen3.8-27B` pinned full HF snapshot at `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`. ms-swift 4.5.3; transformers 5.16.1; bitsandbytes 0.50.2; bfloat16, BNB NF4 4bit, rank 64, alpha 128, dropout .05.
- Training: batch size 1, gradient accumulation 8, lr 5e-5, one epoch, maximum sequence 16,384; `loss_scale=last_round`, `disable_ignore_empty_think=true`, `add_non_thinking_prefix=false`. No Test split provided; validation is for loss and one-input adapter-reload smoke only.
- HF Jobs: namespace `adradar`, existing private bucket `hf://buckets/adradar/storyforge-training`, image `pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime`, `a100-large` (one 80 GB GPU), **110-minute hard timeout**. At currently published HF $2.50/hr A100 hardware price, GPU time upper bound ~**$4.59** per job (not a guaranteed total account bill; excludes independent storage/other charges). Prior v0.1 rank64 baseline evidence supports 80GB feasibility but not guaranteed success for this variant.

## Runner-specific safety
- Separate human-run env `STORYFORGE_ALLOW_PAID_GPU=YES` plus `STORYFORGE_R46_OWNER_EXPERIMENT_ONLY=49_15_ONE_EPOCH` required to call billable `hf jobs run`. Missing approval means no Job submission.
- Data ZIP CRC and SHA256, each original target SHA256, train/validation story separation, known held-out exclusion, code/config SHA256, job uniqueness and GPU capacity all required before model training.
- Frozen original R45 input is sent **only to the existing private HF Bucket**, never ordinary Git, public model repo, or public Dataset.
- Exact job identity `R46_RUN_KEY`, unique private result prefix `experiments/v02-r46/RUN_KEY/` with reports, checkpoint and one-sample adapter reload diagnostic. Success means engineering training completed with finite train and validation loss and persisted Adapter, **not** that it beats Base or v0.1.
- No `git push`/PR merge/remote HF job is triggered by publishing this README. **No HF credentials/tools were available to the assistant to submit the actual paid job.**

## Tested launcher artifact (PRIVATE; not part of ordinary Git)
- `StoryForge_R46_GPU_Experimental_20261014.zip`: SHA256 `72916adf75f9683fb568d037126aae12c8ca39c793894cf9b40f2ec30c88a72d`. Contains exact R45 private ZIP and R46 code/config. The package's SHA256SUMS and ZIP CRC passed; local R45 verification printed `R46_R45_49_15_SOURCE_PASS_EXPERIMENT_ONLY`; a mocked HF CLI reported successful sync/no-GPU and one correct `a100-large --timeout 110m` call in explicit-submit mode; missing GPU env was rejected. **This does not prove remote GPU success.**

## Steps for owner on Mac
```bash
unzip -oq StoryForge_R46_GPU_Experimental_20261014.zip
cd StoryForge_R46_GPU_Experimental_20261014
hf auth whoami
bash r46_submit_hf.sh "$PWD/R45_SOURCE_PRIVATE.zip" sync
STORYFORGE_ALLOW_PAID_GPU=YES STORYFORGE_R46_OWNER_EXPERIMENT_ONLY=49_15_ONE_EPOCH \
  bash r46_submit_hf.sh "$PWD/R45_SOURCE_PRIVATE.zip" submit
```
User records R46_RUN_KEY and HF JOB_ID. Retrieve private `/workspace/experiments/v02-r46/RUN_KEY/r46_training_report.json` and Job logs for verification. If Job fails, **do not submit a second paid job without reading the failure report**.

Remaining external Held-out count **0**; global unknown aliases and exhaustive complete-history canon not independently certified; **model quality promotion prohibited without sealed new evaluation.**
