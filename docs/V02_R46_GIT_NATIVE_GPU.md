# StoryForge v0.2 — R46 Git-native exploratory GPU pilot

**Branch to pull:** `main`. **No ZIP, no new Git LFS objects and no raw story Gold in Git.**

## Why this works

The private HF Bucket already contains (a) R27's frozen 117-line experimental input and (b) the 72/72 PASS R43 CPU Collator JSON report. The R44 and R45 decisions are committed on branch `audit/r40-corrective-execution-20261014`. The launcher pulls *only those existing decision files* using `git fetch/git show`; it downloads the two existing small JSON/JSONL files temporarily from the **private** HF Bucket, reconstructs the R45 candidate JSONL locally, and checks exact SHA256s before provisioning a GPU. No archive download and no new LFS object is needed.

Expected exact R45 SHA256s:

- Train 49: `e7442993088617c4eaefd3a0c9efc7651932f7048f34586046bf6d5b5981a742`
- Validation 15: `5ebbb3c6986a5ac4d294175bab1980ee61df08536f9b8438c8a67010630f1963`
- R27 source 117: `cdecc311f05e2c700f1038f3afca09c889ff681d4ef55dc18dc7426c9d14a92a`

## From the existing Mac checkout

```bash
cd ~/workspace/storyforge
git switch main
git pull --ff-only origin main
hf auth whoami

# No job, no GPU billing; stages small checked code/config only:
bash scripts/v02_r46_submit_git.sh sync

# Explicitly authorize exactly one exploratory paid GPU Job:
STORYFORGE_ALLOW_PAID_GPU=YES \
STORYFORGE_R46_OWNER_EXPERIMENT_ONLY=49_15_ONE_EPOCH \
bash scripts/v02_r46_submit_git.sh submit
```

Submit creates a fresh `R46_RUN_KEY` and prints it. Each invocation stages under a new unique run key; `sync` and `submit` use different keys. **Only `submit` launches** `a100-large`, 110-minute hard timeout, image `pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime`, namespace `adradar`, using Bucket `hf://buckets/adradar/storyforge-training`.

Read logs with `hf jobs logs adradar/JOB_ID` and fetch the report after completion:

```bash
RUN_KEY='r46-...actual...'
hf buckets cp "hf://buckets/adradar/storyforge-training/experiments/v02-r46/$RUN_KEY/r46_training_report.json" \
  ./R46_TRAINING_REPORT_PRIVATE.json
```

If either local checksum check or remote runtime audit fails, **do not rerun the paid GPU submission automatically**. Inspect the failure report first.

## Training contract

One epoch on Qwen3.8-27B pinned revision, 4-bit NF4 / BF16, LoRA rank64 alpha128 dropout0.05, batch1/accum8, learning rate 5e-5, `last_round` only-final-Assistant labels. Before SFT the worker rechecks exact R27-derived R45 rows, checks compiled inputs with the project's actual installed ms-swift, checks GPU memory and runtime config, and preserves outputs in a unique private Bucket prefix. Held-out never goes to SFT.

This is **exploratory** training by owner direction. It does not grant formal dataset or adapter release approval. Independent new Held-out remains pending; Base/v0.1/v0.2 quality claims are prohibited until blind evaluation.

### Main vs draft audit PR

The runnable R46 Git-native scripts are committed directly to `main`, so `git pull` is sufficient. The earlier R40–R46 reviewer/evidence writeups remain on [Draft PR #1](https://github.com/sunxu/storyforge/pull/1) and are **not** a training command.
