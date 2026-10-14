#!/usr/bin/env bash
# R47: stage 20 old prompts directly from Git; no ZIP, no new LFS.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
MODE="${1:-sync}"
[[ "$MODE" == sync || "$MODE" == submit ]] || { echo 'Usage: bash scripts/v02_r47_eval_submit_git.sh [sync|submit]' >&2; exit 2; }
if [[ "$MODE" == submit ]]; then
  [[ "${STORYFORGE_ALLOW_PAID_GPU:-}" == YES ]] || { echo R47_PAID_GPU_NOT_AUTHORIZED >&2; exit 3; }
  [[ "${STORYFORGE_R47_OWNER_BLIND_REGRESSION:-}" == 3_ARMS_20 ]] || { echo R47_SCOPE_NOT_AUTHORIZED >&2; exit 3; }
fi
for command in git python3 hf; do command -v "$command" >/dev/null || { echo "Missing $command" >&2; exit 2; }; done
BUCKET='hf://buckets/adradar/storyforge-training'
P='evaluations/v0.1/test'
python3 scripts/v02_r47_eval_validate.py --prompts "$P/prompts.jsonl" --manifest "$P/manifest.json"
git diff --quiet HEAD -- "$P/prompts.jsonl" "$P/manifest.json" || { echo R47_TRACKED_TEST_CHANGED >&2; exit 2; }
RUN_KEY="r47-$(date -u +%Y%m%dT%H%M%SZ)-$(python3 - <<'PY'
import secrets
print(f'{secrets.randbelow(900000)+100000:06d}')
PY
)"
STAGE="$BUCKET/preflight/v02-r47/git-runs/$RUN_KEY"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/code" "$TMP/private"
for file in v02_r47_eval_validate.py v02_r47_eval_runner.py v02_r47_eval_worker.sh; do
  cp "$ROOT/scripts/$file" "$TMP/code/$file"
done
cp "$ROOT/$P/prompts.jsonl" "$TMP/private/v01_test_prompts.jsonl"
cp "$ROOT/$P/manifest.json" "$TMP/private/v01_test_manifest.json"
python3 - "$TMP" <<'PY'
import hashlib,sys
from pathlib import Path
root=Path(sys.argv[1]); rows=[]
for folder in ('code','private'):
 for file in sorted((root/folder).iterdir()):
  if file.is_file(): rows.append(hashlib.sha256(file.read_bytes()).hexdigest()+'  '+folder+'/'+file.name)
(root/'SHA256SUMS.txt').write_text('\n'.join(rows)+'\n')
print('R47_STAGE_SHA256_PREPARED',len(rows))
PY
for folder in code private; do
  for file in "$TMP/$folder/"*; do hf buckets cp "$file" "$STAGE/$folder/$(basename "$file")"; done
done
hf buckets cp "$TMP/SHA256SUMS.txt" "$STAGE/SHA256SUMS.txt"
echo "R47_GIT_COMMIT=$(git rev-parse HEAD)"
echo "R47_RUN_KEY=$RUN_KEY"
echo "R47_RESULT_PREFIX=$BUCKET/evaluation-runs/v02-r47/$RUN_KEY/"
if [[ "$MODE" == sync ]]; then
  echo 'R47_SYNC_ONLY_NO_GPU'
  exit 0
fi
echo 'R47_SUBMIT_ONE_A100_360_MINUTES_RETROSPECTIVE'
hf jobs run --namespace adradar --name storyforge-v02-r47-three-model-regression \
  --flavor a100-large --timeout 360m \
  --env "STORYFORGE_R47_RUN_KEY=$RUN_KEY" \
  --env STORYFORGE_R47_EVAL_AUTHORIZED=R47_EXPOSED_TEST_20_3_ARM_REVIEW \
  -v "$BUCKET:/workspace:rw" \
  pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime \
  bash "/workspace/preflight/v02-r47/git-runs/$RUN_KEY/code/v02_r47_eval_worker.sh"
