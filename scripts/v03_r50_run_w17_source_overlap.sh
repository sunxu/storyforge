#!/usr/bin/env bash
# Local, read-only R50 W17 triage. Optional --stage-key performs private HF READ only.
set -euo pipefail
umask 077
here="$(cd "$(dirname "$0")" && pwd)"
repo="$(cd "$here/.." && pwd)"
old14="$repo/evaluations/v0.2/training-readiness/20261013/private/original_chat_jsonl_14_20261013.zip"
old15="$repo/evaluations/v0.2/source-archives/06-15/StoryForge_v02_06-15_Full_Evidence_20261013.zip"
[[ -f "$old14" && -f "$old15" ]] || {
  echo 'R50_W17_ORIGINAL_LFS_ARCHIVES_MISSING' >&2; exit 2;
}
python3 "$here/v03_r50_w17_source_overlap.py" \
  --repo "$repo" --old14 "$old14" --old06-15 "$old15" "$@"
