#!/usr/bin/env bash
# Read two immutable original Git LFS archives and five tracked new stories.
# No Hugging Face/GPU/model inference. Optional --push commits aggregate only.
set -euo pipefail
umask 077
MODE="${1:-scan}"
[[ "$MODE" == scan || "$MODE" == --push ]] || {
  echo "Usage: bash scripts/v03_r50_run_full_lfs_world_gate.sh [scan|--push]" >&2
  exit 2
}
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
OLD14="evaluations/v0.2/training-readiness/20261013/private/original_chat_jsonl_14_20261013.zip"
OLD0615="evaluations/v0.2/source-archives/06-15/StoryForge_v02_06-15_Full_Evidence_20261013.zip"
[[ "$(git -C "$REPO" branch --show-current)" == "audit/r49-r50-source-intake-20261015" ]] || {
 echo "R50_LFS_GATE_HOLD__WRONG_BRANCH" >&2; exit 2;
}
git lfs version >/dev/null || { echo "R50_LFS_GATE_HOLD__GIT_LFS_MISSING" >&2; exit 2; }
# Git LFS network usage: ~123 MB. No manual ZIP file handoff via chat.
git -C "$REPO" lfs pull --include="$OLD14,$OLD0615" --exclude=""
python3 -m unittest discover -s "$REPO/tests" \
 -p 'test_v03_r50_full_original_world_inventory.py' -v
ROOT="$HOME/.local/share/storyforge/r50/full-original-worlds"
mkdir -p "$ROOT"
chmod 700 "$ROOT"
RUN="$(mktemp -d "$ROOT/run.XXXXXXXX")"
flags=()
if [[ "$MODE" == --push ]]; then flags+=(--push); fi
python3 "$HERE/v03_r50_full_original_world_inventory.py" \
 --repo "$REPO" --old14 "$REPO/$OLD14" --old06-15 "$REPO/$OLD0615" \
 --output "$RUN/R50_FULL_ORIGINAL_WORLD_INVENTORY_PRIVATE.json" "${flags[@]}"
echo "R50_PRIVATE_AGGREGATE_REPORT=$RUN/R50_FULL_ORIGINAL_WORLD_INVENTORY_PRIVATE.json"
