# StoryForge R54 V2 — pre-paid GPU defect fixed, old stage blocked and NEW sync required

Date: 2026-10-21/22, Asia/Singapore.

**Status:** `OWNER_AUTHORIZED_ONE_R54_A100_JOB__OLD_STAGE_MUST_NOT_SUBMIT__CODE_FIXED__NEW_STAGE_AND_OFFLINE_TESTS_REQUIRED__ZERO_R54_GPU_JOBS_EXECUTED`.

## Owner scope

The Owner replied **“授权”** to the assistant's request for a **single billable R54 V2 HF `a100-large` GPU Job**, hard maximum **120 minutes**, using the already formally released R53 **31 Train / 9 Validation** data, **1 Epoch**, expected **16** optimizer updates, evaluation at 4/8/12/16 and checkpoint saves 8/16. This is authorization for **one** GPU training attempt, **not** unbounded retries, not model promotion, and does not open R50.

## Defect discovered before any GPU billing

The original run key `r54-v2-20261021T155710Z-607779` had been synchronized to a private Bucket without starting a job. Upon inspecting actual R46 successful GPU training evidence, the real ms-swift checkpoint path was:

`/workspace/experiments/v02-r46/r46-20261014T070529Z-248172/output/v0-20261014-070817/checkpoint-7`.

**R54 originally assumed `output/checkpoint-16`** and would incorrectly reject a successful nested `output/v0-.../checkpoint-16`, then point `swift infer --adapters` at a nonexistent path. This is a reproducibility and GPU-cost risk and must be fixed **before** submitting the billable Job.

Changes committed on `main`:
- `scripts/v03_r54_last_step_checkpoint_gate.py`: detect exactly one final checkpoint under either direct `output/checkpoint-16` or actual ms-swift `output/vN-YYYYMMDD-HHMMSS/checkpoint-16`, reject ambiguous/symlinked paths, verify middle checkpoint shares same version directory, return exact absolute and relative path.
- `scripts/v03_r54_gpu_runner.py`: pass discovered `final_checkpoint_path` directly to real adapter reload/inference.
- `scripts/v03_r54_gpu_submit.sh`: before any billable attempt marker and `hf jobs run`, **download** the staged `SHA256SUMS.txt` and compare all seven exact code-file digests, config digest, two frozen datasets, formal R53 data-only receipt and CPU40 report/intake hashes against current local code and pinned evidence. Stale GPU-stage code is always `R54_REMOTE_STAGE_CODE_OR_EVIDENCE_DRIFT__RESYNC_NEW_KEY`; it must never be submitted.
- Three additional checkpoint-path tests and two new GPU-pipeline static tests were added. The source now contains **15** checkpoint cases and **27** GPU-pipeline cases. They are **authored but not executed in the assistant's current container**; Owner should run both on Mac and refuse submit if either fails.

## Strict resynchronization

**Do not run `submit` with the old key `r54-v2-20261021T155710Z-607779`** and do not overwrite or delete that existing private Bucket stage. The corrected worker must be staged under a **fresh run key** using exactly the same frozen 31/9 data and training contract. This is still within the authorized **one unstarted GPU attempt**; no GPU Job has been launched yet.

User workflow:
1. `git switch main && git pull --ff-only origin main`.
2. Run the separate 27-case and 15-case unittests and `bash -n` validation (42 cases total, results **not yet supplied**). Stop if any fail.
3. `bash scripts/v03_r54_gpu_submit.sh sync "<R53 formal release directory>" "<R53 CPU report>" "<R53 CPU intake>"`. Get **NEW** `R54_RUN_KEY`. Verify `R54_REMOTE_STAGE_COMPLETE__NO_GPU_JOB`.
4. `python3 scripts/v03_r54_gpu_remote_guard.py ready "<NEW_RUN_KEY>"` — only confirms complete objects and no prior paid attempt marker.
5. Only after all prior checks pass, invoke `STORYFORGE_ALLOW_PAID_GPU=YES STORYFORGE_R54_OWNER_GPU_SCOPE=R54_31_9_V2_16STEP_ONE_EPOCH bash scripts/v03_r54_gpu_submit.sh submit "<NEW_RUN_KEY>"`.

The newer submit gate detects old-code SHA mismatches **before** GPU billing. Submission logs may contain an actual HF Job ID. Do not retry automatically when Job initiation is uncertain; check HF Jobs state first.

All private narrative data, adapter weights and R50 stay outside ordinary Git. No remote A100 GPU Job was called by this corrective commit; no R54 training completion or checkpoint is claimed.

## Validation scope

Original previously executed offline R54 planning tests **27/27** and GitHub source-read static checks **15/15** were performed before this correction. They are **not** tests of the newly corrected pipeline. Freshly authored current regression suites contain **42 cases** and require execution in the Owner environment before paid submit.

**Old prepared-stage evidence remains recorded** in `docs/evidence/V03_R54_V2_REMOTE_STAGE_OWNER_RECEIPT_20261021.md`, but no longer denotes a safe-to-submit code snapshot.
