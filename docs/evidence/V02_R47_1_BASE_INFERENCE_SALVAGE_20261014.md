# StoryForge v0.2 — R47.1 partial Base salvage after first GPU review job

**Date: 2026-10-14. State: recovery scripts committed; HF remote Base result still requires a CPU-only read/check. No resumed paid job has been submitted here.**

## Failure facts from owner-provided HF Jobs log
- Failed Job `6acf3b8fc66288145223b41e`; run key `r47-20261014T082109Z-820409`.
- The Base inference returned **20/20 generated samples**, 10,303 tokens in 1,436.43 seconds, and ms-swift reported saving `/workspace/evaluation-runs/v02-r47/r47-20261014T082109Z-820409/base-results.jsonl`.
- After inference completed, the old validator failed at sample 0: `ValueError: prompt/context mismatch at 0`. No v0.1 or v0.2 inference began, no blind package was generated; Job exit code 2 / stage ERROR. **GPU training was not performed**.
- Original validator compared `row['messages'] == prompt['messages']` including all fields. ms-swift result serialization can add e.g. `loss: null` and/or an appended generated Assistant message; either changes object equality without necessarily changing the original prompt. [Upstream result example](https://github.com/modelscope/ms-swift/issues/6916). **The actual bytes of the saved Base file have not yet been inspected in this conversation; this is a credible technical cause, not confirmed incident root cause until the CPU-only recovery check passes.**

## Fix, without weakening prompt evidence
- Updated `scripts/v02_r47_eval_validate.py` to compare the input prefix by every original turn's exact **role AND content** and refuse reordered, shortened or altered prompts, loss=true, missing/blank responses, and unrelated appended messages.
- Allow only optional nonsupervising `loss:null/false` fields and, if present, exactly one appended Assistant whose text is exactly the `response` field. No output can be aligned merely by row position when its original context differs.
- Unit tests now include normal output, null-loss plus appended Assistant, changed System, corrupted appended Assistant, displaced row, wrong prompt SHA and forbidden supervision. R47 no-GPU CI passed following this fix.

## Recovery route: reuse Base, pay only for remaining two arms
- Added `scripts/v02_r47_recover_git.sh check` as a **Mac-only CPU/no-GPU** preflight. Downloads only the two existing small private objects from the failed Job: `R47_PRIVATE_RUN_REPORT.json`, `base-results.jsonl`. Validates old run-key/status, test prompt/manifest SHA256 and strict full-prefix role/content for **all 20 outputs**. Does not print raw story text or responses.
- If and only if `check` prints `R47_RECOVERY_BASE_20_20_PASS` and `R47_RECOVERY_CHECK_PASS_NO_GPU`, owner may explicitly authorize a fresh recovery HF GPU Job via `STORYFORGE_ALLOW_PAID_GPU=YES STORYFORGE_R47_OWNER_RECOVER_ONLY=V01_V02_20 bash scripts/v02_r47_recover_git.sh submit`.
- Submission creates a **new** unique run key. The GPU worker verifies persisted previous report and Base response hashes again, copies the exact 20 Base results to the new private output directory, and only runs v0.1 and v0.2 inference; then builds the same blinded 60 responses and three scoring sheets.
- Adapter SHA checks for both checkpoints remain in place. The original failed Job outputs stay untouched. No ZIP, no Git LFS, no test Gold, no training or optimizer.
- Resumed GPU timeout: **240 minutes hard cap** for the remaining two arms, a separate billable HF A100 Job. Do not submit it if the local check is blocked or the output object is absent; then diagnose rather than rerun Base.

## Source and output destinations
- Private HF root: `hf://buckets/adradar/storyforge-training`.
- Saved Base file expected under `evaluation-runs/v02-r47/r47-20261014T082109Z-820409/base-results.jsonl`.
- A successful new result report and blind package will be under `evaluation-runs/v02-r47/NEW_RUN_KEY/`.
- Expected final marker: `R47_THREE_MODEL_REGRESSION_GENERATION_PASS_NOT_PROMOTED`. This is a **retrospective old exposed 20-item regression**, not a newly sealed independent Held-out and not a model-promotion approval.

**Never rerun original full `v02_r47_eval_submit_git.sh submit` for this failure without investigating saved Base inference.**
