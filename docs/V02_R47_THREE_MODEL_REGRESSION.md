# StoryForge v0.2 — R47 three-arm retrospective regression blind review

**2026-10-14 · Operationally prepared / NO GPU evaluation Job launched by this documentation.**

## Purpose and scientific limitations

Re-use the **20 previously exposed v0.1 Test prompts** for regression diagnosis only. Generate **60 brand-new responses** under the same input context and generation parameters using:

- **Base:** Qwen/Qwen3.8-27B, pinned revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`.
- **v0.1:** original checkpoint-9 in the existing private HF bucket, adapter weights SHA256 `621d7328056758607c9d7797282ae4d5803cdb1727dab6b40a321ee959dd2478`.
- **v0.2:** R46 checkpoint-7, adapter weights SHA256 `bec4ba74d858db3ff117d581478ef9cac41b1ecc7ea2a67523f6db1096addf2b`.

This is **not a fresh Held-out test**. Past v0.1 outputs and reviewer notes were already disclosed and used for analysis. Use only to diagnose whether the R46 v0.2 adapter resolves *known failures*, not to claim independent generalization or model promotion. The owner is separately preparing new independent Held-out.

The original v0.1 Test embeds rich story/character cards in System text, whereas R46 v0.2 was trained on generic **no-card** System messages. Every arm will receive **the exact same historical Test input** for a controlled comparison, but report this task-contract mismatch; it can disadvantage the newer no-card adapter, and is not a perfect test of its intended deployment contract.

## Immutable inputs

- Git tracked source: `evaluations/v0.1/test/prompts.jsonl` and `evaluations/v0.1/test/manifest.json`.
- Original 20-case `storyforge-blind-v1` manifest; no original Gold answer, original model answer key, historical grader scores or original paired response file is copied into the R47 inference environment.
- Prompt hashes are recomputed per sample from the exact messages and compared to the original manifest; no prompt is rewritten.
- Existing Git-native checkout, **no new ZIP and no Git LFS**. Only the same 20 old prompts and small scripts are copied to a unique prefix of `hf://buckets/adradar/storyforge-training`.

## Same-condition inference

HF Jobs `--namespace adradar --flavor a100-large`, image `pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime`, 360-minute hard timeout. This is a worst-case guardrail, not an expected duration or price guarantee; a full three-arm, 1536-token evaluation can take considerably longer than a single R46 128-token adapter reload test.

Versions: `ms-swift==4.5.3`, `transformers==5.16.1`, `bitsandbytes==0.50.2`; pinned Qwen model SHA; bfloat16/NF4 4-bit, `temperature=0`, `max_new_tokens=1536`, `seed=42`, `data_seed=42`, no shuffle.

Read-only checkpoint guards independently hash both adapter weight files before inference. No `swift sft`, optimizer, training labels or test targets are used.

## Execute from the existing Mac Git checkout

```bash
cd ~/workspace/storyforge
git switch main
git pull --ff-only origin main
hf auth whoami

# No paid Job:
bash scripts/v02_r47_eval_submit_git.sh sync

# Submit NEW paid GPU evaluation ONLY when explicitly authorized:
STORYFORGE_ALLOW_PAID_GPU=YES \
STORYFORGE_R47_OWNER_BLIND_REGRESSION=3_ARMS_20 \
  bash scripts/v02_r47_eval_submit_git.sh submit
```

**Save the new `R47_RUN_KEY` from the submit invocation** (sync and submit create different keys), and the HF `JOB_ID`. Read logs:

```bash
hf jobs logs adradar/JOB_ID
```

Expected successful report `R47_THREE_MODEL_REGRESSION_GENERATION_PASS_NOT_PROMOTED` at:

```text
hf://buckets/adradar/storyforge-training/evaluation-runs/v02-r47/R47_RUN_KEY/R47_PRIVATE_RUN_REPORT.json
```

Note: job outputs are under `evaluation-runs/v02-r47` (not the staging prefix `preflight/v02-r47/git-runs`).

### Anonymous blind review package

On successful completion, the Job creates:

```text
evaluation-runs/v02-r47/R47_RUN_KEY/review-package/blind-review/
  R47_BLIND_THREE_WAY_20.jsonl
  R47_Reviewer_01.csv
  R47_Reviewer_02.csv
  R47_Reviewer_03.csv
evaluation-runs/v02-r47/R47_RUN_KEY/review-package/private/
  R47_PRIVATE_ANSWER_KEY.json
  R47_AUDIT_SUMMARY.json
```

**Never send the answer key, model-named result JSONL, complete run report, or old scoring files to blinded reviewers.** Send each reviewer only their own R47 CSV. Key is separately placed under `private/`, randomized per sample independently of the previously published v0.1 A/B order.

Each reviewer reads the world/system text, history and current User message, scores **A/B/C** on six dimensions 1–5 (narrative continuity, character consistency, instruction adherence, literary writing, interactive progression, player agency), picks `A/B/C/TIE`, cites exact evidence, records any severe failure, and explicitly writes `无` if none. Do not share ratings between reviewers before collection.

Run this locally after collecting all three completed CSVs, using the ORIGINAL frozen manifest:

```bash
python3 scripts/v02_r47_review_aggregate.py \
  --manifest evaluations/v0.1/test/manifest.json \
  --reviews R47_Reviewer_01.csv R47_Reviewer_02.csv R47_Reviewer_03.csv
```

This validates completeness **without reading the answer key**. Only after all three reviewers' judgments are frozen should the coordinator execute:

```bash
python3 scripts/v02_r47_review_aggregate.py \
  --manifest evaluations/v0.1/test/manifest.json \
  --reviews R47_Reviewer_01.csv R47_Reviewer_02.csv R47_Reviewer_03.csv \
  --key R47_PRIVATE_ANSWER_KEY.json \
  --output R47_PRIVATE_UNBLIND_DIAGNOSTIC.json
```

The report shows raw three-model preferences, two-or-more reviewer majorities, six-dimension means and per-case failure labels. Also report results separately for both original Test story worlds (original data has two), review reasons and uncertainty. **No statistical proof of broad generalization can be inferred from 20 previously exposed prompts.**

## Failure and release policy

- A missing, modified or unexpected prompt, adapter hash mismatch, missing response, wrong context, incomplete review, or mixed answer key fails closed.
- If a paid run fails or reaches its timeout, **do not automatically resubmit**. Preserve partial arm outputs and diagnose the Job logs first.
- GPU inference authorization is **new and separate from R46 training permission**. Without both explicit environment variables the launcher refuses to submit.
- Training data / Adapter checkpoint files are never committed to ordinary Git or re-trained; results remain in the existing **private** Bucket.
- Model promotion remains **NOT_APPROVED** until truly new independently authored, sealed Held-out is run under a predeclared rubric.

**Checkpoint:** `R47_THREE_ARM_OLD_EXPOSED_TEST_REGRESSION_READY__NOT_A_MODEL_QUALITY_PASS`.
