#!/usr/bin/env bash
# Run from a git-updated StoryForge checkout. No ZIP download and no new LFS.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
ACTION="${1:-sync}"
[[ "$ACTION" == sync || "$ACTION" == submit ]] || {
  echo 'Usage: bash scripts/v02_r46_submit_git.sh [sync|submit]' >&2; exit 2;
}
if [[ "$ACTION" == submit ]]; then
  [[ "${STORYFORGE_ALLOW_PAID_GPU:-}" == YES ]] || {
    echo R46_GPU_SUBMIT_NOT_AUTHORIZED >&2; exit 3;
  }
  [[ "${STORYFORGE_R46_OWNER_EXPERIMENT_ONLY:-}" == 49_15_ONE_EPOCH ]] || {
    echo R46_EXPERIMENT_SCOPE_NOT_AUTHORIZED >&2; exit 3;
  }
fi
command -v hf >/dev/null || { echo "HF CLI missing" >&2; exit 2; }
command -v python3 >/dev/null || { echo "python3 missing" >&2; exit 2; }
command -v git >/dev/null || { echo "git missing" >&2; exit 2; }

BUCKET="hf://buckets/adradar/storyforge-training"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/code" "$TMP/scripts"

# Fetch only already-written R44/R45 decision metadata. No original story data.
git fetch --quiet --no-tags origin audit/r40-corrective-execution-20261014
git show FETCH_HEAD:docs/evidence/V02_R44_ENGINEERING_SUBSET_AND_RELEASE_GATE_20261014.json > "$TMP/r44.json"
git show FETCH_HEAD:docs/evidence/V02_R45_PHASE1_SCOPED_CONTENT_WORLD_GATE_20261014.json > "$TMP/r45.json"

# Download the existing 22KB private *JSON report*, never a training ZIP.
R43="$BUCKET/preflight/v02-r43/results/r43-20261014T041047Z-26516/R43_HF_RUNTIME_REPORT_PRIVATE_v2.json"
hf buckets cp "$R43" "$TMP/r43.json"
python3 "$ROOT/scripts/v02_r46_manifest_from_evidence.py" \
  --r43-report "$TMP/r43.json" --r44-gate "$TMP/r44.json" \
  --r45-gate "$TMP/r45.json" --output "$TMP/code/manifest.json"

# The exact R27 source already exists in the private bucket from the prior CPU Job.
hf buckets ls "$BUCKET/preflight/v02-r27/private/" > "$TMP/inputs_listing.txt"
grep -q 'r27_private_candidate_117_NOT_APPROVED.jsonl' "$TMP/inputs_listing.txt" || {
  echo R46_PRIVATE_R27_SOURCE_NOT_FOUND >&2; exit 2;
}

RUN_KEY="r46-$(date -u +%Y%m%dT%H%M%SZ)-$(python3 - <<'PY'
import secrets
print(f"{secrets.randbelow(900000)+100000:06d}")
PY
)"
STAGE="$BUCKET/preflight/v02-r46/git-runs/$RUN_KEY"
for file in v02_r46_build_dataset.py v02_r46_gpu_runner.py v02_r46_gpu_worker.sh; do
  cp "$ROOT/scripts/$file" "$TMP/code/$file"
done
cp "$ROOT/configs/v02_r46_experimental_qlora.yaml" "$TMP/code/r46_config.yaml"
for file in hf_label_mask_audit.py hf_cpu_preflight.py hf_smoke_guard.py hf_job_runner.py prepare_sft.py; do
  cp "$ROOT/scripts/$file" "$TMP/scripts/$file"
done

python3 - "$TMP" <<'PY'
from pathlib import Path
import hashlib,sys
root=Path(sys.argv[1])
lines=[]
for folder in ("code","scripts"):
    for file in sorted((root/folder).iterdir()):
        if file.is_file():
            lines.append(hashlib.sha256(file.read_bytes()).hexdigest()
                         +"  "+folder+"/"+file.name)
(root/"CODE_SHA256SUMS.txt").write_text("\n".join(lines)+"\n")
print("R46_CODE_SHA256SUMS_PASS",len(lines))
PY
for folder in code scripts; do
  for path in "$TMP/$folder/"*; do
    hf buckets cp "$path" "$STAGE/$folder/$(basename "$path")"
  done
done
hf buckets cp "$TMP/CODE_SHA256SUMS.txt" "$STAGE/CODE_SHA256SUMS.txt"
echo "R46_GIT_COMMIT=$(git rev-parse HEAD)"
echo "R46_RUN_KEY=$RUN_KEY"
echo "R46_RESULT_PREFIX=$BUCKET/experiments/v02-r46/$RUN_KEY/"
if [[ "$ACTION" == sync ]]; then
  echo R46_SYNC_ONLY_NO_GPU
  exit 0
fi

echo R46_SUBMIT_SINGLE_A100_110_MINUTES
hf jobs run --namespace adradar --name storyforge-v02-r46-git-pilot \
  --flavor a100-large --timeout 110m \
  --env "STORYFORGE_R46_RUN_KEY=$RUN_KEY" \
  --env STORYFORGE_EXPERIMENTAL_GPU_AUTHORIZED=R46_ONE_EPOCH_49_15_EXPLORE \
  -v "$BUCKET:/workspace:rw" \
  pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime \
  bash "/workspace/preflight/v02-r46/git-runs/$RUN_KEY/code/v02_r46_gpu_worker.sh"
