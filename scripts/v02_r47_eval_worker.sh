#!/usr/bin/env bash
# R47 three-arm retrospective evaluation; no optimizer, no model training.
set -euo pipefail
: "${STORYFORGE_R47_RUN_KEY:?RUN_KEY required}"
[[ "$STORYFORGE_R47_RUN_KEY" =~ ^r47-[0-9TZ-]+-[0-9]{6}$ ]] || { echo R47_INVALID_RUN_KEY >&2; exit 2; }
[[ "${STORYFORGE_R47_EVAL_AUTHORIZED:-}" == 'R47_EXPOSED_TEST_20_3_ARM_REVIEW' ]] || { echo R47_NOT_AUTHORIZED >&2; exit 3; }
ROOT="/workspace/preflight/v02-r47/git-runs/$STORYFORGE_R47_RUN_KEY"
exec python -u "$ROOT/code/v02_r47_eval_runner.py" --run-key "$STORYFORGE_R47_RUN_KEY" --stage "$ROOT"
