#!/usr/bin/env bash
# R47.1 rescue: check already generated Base on Mac, then run v0.1/v0.2 only.
# No ZIP, no LFS, no optimizer, no old Base regeneration.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
MODE="${1:-check}"
[[ "$MODE" == check || "$MODE" == submit ]] || { echo 'Usage: bash scripts/v02_r47_recover_git.sh [check|submit]' >&2; exit 2; }
if [[ "$MODE" == submit ]]; then
  [[ "${STORYFORGE_ALLOW_PAID_GPU:-}" == YES ]] || { echo R47_RECOVERY_GPU_NOT_AUTHORIZED >&2; exit 3; }
  [[ "${STORYFORGE_R47_OWNER_RECOVER_ONLY:-}" == V01_V02_20 ]] || { echo R47_RECOVERY_SCOPE_NOT_AUTHORIZED >&2; exit 3; }
fi
for command in git python3 hf; do
  command -v "$command" >/dev/null || { echo "Missing $command" >&2; exit 2; }
done
BUCKET='hf://buckets/adradar/storyforge-training'
OLD_KEY='r47-20261014T082109Z-820409'
OLD="$BUCKET/evaluation-runs/v02-r47/$OLD_KEY"
P='evaluations/v0.1/test'
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
# Read original failed-run metadata and saved Base output, no paid HF Jobs.
hf buckets cp "$OLD/R47_PRIVATE_RUN_REPORT.json" "$TMP/old_report.json"
hf buckets cp "$OLD/base-results.jsonl" "$TMP/base-results.jsonl"
python3 - "$TMP" "$OLD_KEY" "$P/prompts.jsonl" "$P/manifest.json" <<'PY'
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'scripts'))
from v02_r47_eval_validate import validate_prompts,validate_responses
folder=Path(sys.argv[1]);oldkey=sys.argv[2]
prompts=Path(sys.argv[3]);manifest=Path(sys.argv[4])
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((folder/'old_report.json').read_text())
if (r.get('run_key')!=oldkey or r.get('status')!='BLOCKED'
    or r.get('training_performed') is not False
    or r.get('input',{}).get('prompts_sha256')!=h(prompts)
    or r.get('input',{}).get('manifest_sha256')!=h(manifest)):
    raise SystemExit('R47_RECOVERY_REPORT_OR_PROMPT_MISMATCH')
data,_=validate_prompts(prompts,manifest)
results=validate_responses(folder/'base-results.jsonl',data)
if len(results)!=20:raise SystemExit('R47_RECOVERY_BASE_COUNT_MISMATCH')
print('R47_RECOVERY_BASE_20_20_PASS sha256='+h(folder/'base-results.jsonl'))
print('R47_SOURCE_JOB='+oldkey)
PY
if [[ "$MODE" == check ]]; then
  echo R47_RECOVERY_CHECK_PASS_NO_GPU
  exit 0
fi
RUN_KEY="r47-$(date -u +%Y%m%dT%H%M%SZ)-$(python3 - <<'PY'
import secrets
print(f'{secrets.randbelow(900000)+100000:06d}')
PY
)"
STAGE="$BUCKET/preflight/v02-r47/git-runs/$RUN_KEY"
mkdir -p "$TMP/code" "$TMP/private"
for file in v02_r47_eval_validate.py v02_r47_eval_runner.py v02_r47_eval_worker.sh; do
  cp "$ROOT/scripts/$file" "$TMP/code/$file"
done
cp "$ROOT/$P/prompts.jsonl" "$TMP/private/v01_test_prompts.jsonl"
cp "$ROOT/$P/manifest.json" "$TMP/private/v01_test_manifest.json"
python3 - "$TMP" <<'PY'
from pathlib import Path
import hashlib,sys
root=Path(sys.argv[1]);rows=[]
for folder in ('code','private'):
    for p in sorted((root/folder).iterdir()):
        if p.is_file():
            rows.append(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+folder+'/'+p.name)
(root/'SHA256SUMS.txt').write_text('\n'.join(rows)+'\n')
print('R47_RECOVERY_STAGE_HASHES_PASS',len(rows))
PY
for folder in code private; do
  for file in "$TMP/$folder/"*; do
    hf buckets cp "$file" "$STAGE/$folder/$(basename "$file")"
  done
done
hf buckets cp "$TMP/SHA256SUMS.txt" "$STAGE/SHA256SUMS.txt"
echo "R47_RECOVERY_GIT_COMMIT=$(git rev-parse HEAD)"
echo "R47_NEW_RUN_KEY=$RUN_KEY"
echo "R47_ORIGINAL_BASE_RUN_KEY=$OLD_KEY"
echo "R47_NEW_RESULT_PREFIX=$BUCKET/evaluation-runs/v02-r47/$RUN_KEY/"
echo R47_SUBMIT_V01_V02_ONLY_A100_240M
hf jobs run --namespace adradar --name storyforge-v02-r47-resume-v01-v02 \
  --flavor a100-large --timeout 240m \
  --env "STORYFORGE_R47_RUN_KEY=$RUN_KEY" \
  --env "STORYFORGE_R47_REUSE_BASE_RUN_KEY=$OLD_KEY" \
  --env STORYFORGE_R47_EVAL_AUTHORIZED=R47_EXPOSED_TEST_20_3_ARM_REVIEW \
  -v "$BUCKET:/workspace:rw" \
  pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime \
  bash "/workspace/preflight/v02-r47/git-runs/$RUN_KEY/code/v02_r47_eval_worker.sh"
