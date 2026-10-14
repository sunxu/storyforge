#!/usr/bin/env bash
# StoryForge R46 GPU worker: only a previously approved bounded experiment.
set -euo pipefail
RUN_KEY="${STORYFORGE_R46_RUN_KEY:?missing run key}"
[[ "$RUN_KEY" =~ ^r46-[0-9TZ-]+-[0-9]{6}$ ]] || { echo R46_INVALID_RUN_KEY >&2; exit 2; }
[[ "${STORYFORGE_EXPERIMENTAL_GPU_AUTHORIZED:-}" == R46_ONE_EPOCH_49_15_EXPLORE ]] || { echo R46_GPU_NOT_AUTHORIZED >&2; exit 3; }
STAGE="/workspace/preflight/v02-r46/git-runs/$RUN_KEY"
export PYTHONPATH="$STAGE/code${PYTHONPATH:+:$PYTHONPATH}"
exec python -u "$STAGE/code/v02_r46_gpu_runner.py" --stage "$STAGE" --run-key "$RUN_KEY"
