# R60-00 GitHub and Worktree Audit

> Date: 2026-11-04  
> Status: GITHUB_BASELINE_VERIFIED / LOCAL_WORKTREE_RECHECK_BLOCKED  
> Scope: metadata and repository structure only; no private data read.

## 1. GitHub repository verification

Verified through the GitHub repository interface:

| Check | Result |
|---|---|
| Repository | `sunxu/storyforge` |
| Visibility | Private |
| Default branch | `main` |
| Write permission | Available |
| Approved base branch | `gold-quality/quality-v1-sft-candidates` |
| Approved base SHA | `adc3876d6d0350c270e2b5fa5ccc832438fdf7ee` |
| Base commit title | `test(r59): cover normalized HF input mount metadata` |
| Base branch vs approved SHA | identical; ahead 0 / behind 0 |
| Target branch before creation | not found |
| Target branch creation | successful from the exact approved SHA |
| New target branch | `r60/hf-jobs-runtime` |

The target branch was created on GitHub from the exact approved commit. The first R60 commit adds only this architecture document; comparison reports one commit ahead, zero behind, and one added documentation file.

## 2. Protected source verification

The blob SHA of `src/storyforge_dataset/token_preflight.py` at the approved base and on the R60 branch is identical:

`9ea7596c2151ee10aa1394beed8ab363a584aeb1`

Therefore the shared token preflight source was not modified by R60-00.

The existing `scripts/hf_job_guard.py` was inspected read-only. It is a narrow CPU-only job policy guard and remains outside the new Runtime core; R60 must not duplicate its job-submission policy or add job submission to the Runtime.

The project manifest declares Python `>=3.11`, no core runtime dependencies, and optional development dependencies `pytest>=8.0`, `ruff>=0.8`, `PyYAML>=6.0`.

## 3. Local Worktree safety — limitation

The current tool execution environment does not mount the owner's macOS path `/Users/keedle/workspace`. A direct filesystem check returned “No such file or directory”. Consequently, this execution cannot independently re-read the live local Worktree registry or local filesystem status.

The following inventory was supplied by the Owner in the current task context; it is recorded as an observed snapshot, NOT as a fresh live verification:

| Worktree | Branch | HEAD | Supplied status |
|---|---|---|---|
| `storyforge` | `main` | `701ab9c` | clean |
| `storyforge-gold-quality` | `gold-quality/quality-v1-sft-candidates` | `adc3876` | untracked `2.sh`, `run.py`, `run.sh` |
| `storyforge-r55-tooling` | `r57/v03b-data-design` | `4dd144d` | untracked `R57_BPROMPT_DEV20_BLIND_PAIR_REVIEW_OWNER_PRIVATE.csv` |
| `storyforge-r59-strict28-exposure-20261103` | `r59/strict28-history-exposure` | `a458bb2` | clean |

No supplied untracked file has been touched, moved, deleted, staged or committed. No local Worktree has been created from this environment.

## 4. Required local handoff gate

Before creating the local R60 Worktree, run on the Owner's Mac:

```bash
set -euo pipefail
REPO="$HOME/workspace/storyforge-gold-quality"
TARGET="$HOME/workspace/storyforge-r60-hf-jobs-runtime"

git -C "$REPO" rev-parse --show-toplevel
git -C "$REPO" rev-parse HEAD
git -C "$REPO" status --short --branch
git -C "$REPO" worktree list --porcelain

# Must match the approved commit exactly.
test "$(git -C "$REPO" rev-parse HEAD)" = "adc3876d6d0350c270e2b5fa5ccc832438fdf7ee"

# Do not overwrite or reuse an existing path.
test ! -e "$TARGET"

# Fetch and verify the newly created remote branch before adding its worktree.
git -C "$REPO" fetch origin r60/hf-jobs-runtime
test "$(git -C "$REPO" rev-parse FETCH_HEAD)" = "7e37622b66613cda432227c9e5b7f754a1890e49"

git -C "$REPO" worktree add -b r60/hf-jobs-runtime "$TARGET" FETCH_HEAD
git -C "$TARGET" status --short --branch
git -C "$TARGET" rev-parse HEAD
```

If the local target branch or path already exists, stop and inspect; do not force, reset, prune, or delete any Worktree. The untracked files listed above must remain untouched.

## 5. R60-00 conclusion

- GitHub repository and approved base: VERIFIED.
- Remote target branch: CREATED from the exact approved SHA.
- Architecture baseline: frozen in `docs/standards/R60_HF_JOBS_RUNTIME_ARCHITECTURE_V1_CN.md`.
- `token_preflight.py`: unchanged.
- Local Worktree inventory: owner-provided snapshot available; live recheck BLOCKED by unavailable Mac filesystem.
- Local Worktree creation, local tests, GitHub CI, and HF CPU Smoke: NOT RUN.

R60 implementation must not begin in an assumed local Worktree until the owner-side handoff gate has completed and the target Worktree is confirmed clean.
