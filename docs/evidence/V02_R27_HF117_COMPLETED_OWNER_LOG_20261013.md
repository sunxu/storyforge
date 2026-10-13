# StoryForge v0.2 — R27 full 117 no-training HF job completion (owner log)

Date: 2026-10-13. Admission remains **`PENDING_NOT_APPROVED`**. The original 195 Gold and quarantines remain unchanged.

## User-provided remote run evidence

- HF namespace `adradar`, HF Job `6ace19935ccb47ba0f787af5`, user-reported stage `completed`.
- Terminal line: `R27_ACTUAL_INPUT_GATE REMOTE_FINAL_INPUT_DIAGNOSTIC_ONLY 117 / 117 ADMISSION=PENDING_NOT_APPROVED`.
- The last printed sample (`sample=117`) records `tokens=1694`, `supervised_tokens=137`, historical Assistant, System and User supervised tokens all **0**, final Assistant content tokens **135**, template suffix tokens **2**, counterfactual supervised tokens **2**, `status=PASS`.
- The R27 script checks immutable provisional candidate JSONL SHA256 `cdecc311f05e2c700f1038f3afca09c889ff681d4ef55dc18dc7426c9d14a92a`, pinned Qwen revision, authentic ms-swift `last_round` labels and actual collator consistency. The completed-job terminal signal indicates **117/117 remote program checks passed**.
- **Evidence level:** `OWNER_LOG_REPORTED_PASS`. The machine-readable `r27_hf_final_input_report.json` is not yet present in GitHub and has not been independently verified. Report-wide token statistics, per-sample labels SHA256, package versions and the run key must be read from the actual JSON, not inferred from the terminal sample.

## Pre-GPU source backup is now remote verified

GitHub commit `81a081a3e5400e356aa72d34235ed3d52d8ae816` uploaded the four private pre-GPU Git LFS artifacts. [Actions run 38398541882](https://github.com/sunxu/storyforge/actions/runs/38398541882) completed SUCCESS and downloaded the LFS objects before computing four SHA256s, matching the immutable archive manifest. This is much stronger than checking LFS pointer files only; the input resources are recoverable from the private repository with current access.

## Still blocked from formal GPU SFT

The 117 candidates remain a private derived `NOT_APPROVED` diagnostic dataset. The 96 Train / 21 Validation story-UUID split is a **proposal**. No independent unseen v0.2 held-out collection, complete linked-world/alias split graph, finalized content/age clearance or request-time-canon/no-card derivative authorization has passed. A remote diagnostic PASS does not approve dataset promotion, training a production adapter, or a paid GPU job.

## Finish evidence transfer

Obtain the original report from the existing HF private Bucket under `preflight/v02-r27/results/<R27_RUN_KEY>/r27_hf_final_input_report.json`. Use `hf buckets ls` to locate the run key if needed. Then verify with the repository's `scripts/v02_verify_r27_hf_report.py` using the Git-LFS-backed `R27_HF117_Fix_20261013.zip` and archive only the actual original JSON plus its SHA256. This document is an additive reported finding, not a change to the previous frozen R27 gate JSON.
