#!/usr/bin/env bash
# StoryForge v0.2 R18 private HF CPU diagnostics, NO TRAINING.
set -euo pipefail
cd "$(dirname "$0")/.."
BUCKET="hf://buckets/adradar/storyforge-training"
PREFIX="${BUCKET}/preflight/v02-r18"
R17_ZIP="${1:-}"
MODE="${2:-sync}"
STAGE="${STORYFORGE_R18_STAGE:-both}"
if [[ -z "$R17_ZIP" || ! -s "$R17_ZIP" ]]; then
  echo "Usage: bash scripts/v02_r18_submit_hf.sh /path/to/StoryForge_v02_R17_Runtime_And_Label_Contract_20261013.zip [sync|submit]" >&2; exit 2
fi
if [[ "$MODE" != sync && "$MODE" != submit ]]; then
  echo "MODE must be sync or submit" >&2; exit 2
fi
if [[ "$STAGE" != token && "$STAGE" != both ]]; then
  echo "STORYFORGE_R18_STAGE must be token or both" >&2; exit 2
fi
command -v hf >/dev/null || { echo "HF CLI required: pip install -U huggingface_hub" >&2; exit 2; }
python3 - "$R17_ZIP" <<'PY'
import sys, zipfile, hashlib
p=sys.argv[1]
expected="ba42ad7568ce0ca3ab8b3d218397006b430affc9f1b2f74b7ea4392e5103eab3"
actual=hashlib.sha256(open(p,"rb").read()).hexdigest()
assert actual==expected, "R17 ZIP SHA256 mismatch"
with zipfile.ZipFile(p) as z:
    assert any(n.endswith("/R18_EXECUTION_CONTRACT.md") for n in z.namelist()), "Wrong archive"
    assert any(n.endswith("/baseline/StoryForge_v02_R16_Offline_Engineering_Preflight_20261013.zip") for n in z.namelist()), "No R16 baseline"
print("R17 PRIVATE SOURCE HASH PASS; no training.")
PY
for f in scripts/v02_r18_hf_no_train.py scripts/v02_r18_hf_worker.sh scripts/hf_label_mask_audit.py; do
  hf buckets cp "$f" "$PREFIX/code/$(basename "$f")"
done
hf buckets cp "$R17_ZIP" "$PREFIX/private/StoryForge_v02_R17_Runtime_And_Label_Contract_20261013.zip"
echo "SYNCED to private HF bucket; no job launched."
if [[ "$MODE" == sync ]]; then exit 0; fi
if [[ "${STORYFORGE_ALLOW_PAID_CPU:-}" != YES ]]; then
  echo "REFUSED: set STORYFORGE_ALLOW_PAID_CPU=YES to authorize paid CPU diagnostics" >&2; exit 3
fi
if [[ "$STAGE" == both ]]; then
  IMAGE="pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime"
else
  IMAGE="python:3.11-slim"
fi

RUN_KEY="r18-$(date -u +%Y%m%dT%H%M%SZ)-${RANDOM}"
echo "R18_RUN_KEY=$RUN_KEY"
echo "R18_RESULT_PREFIX=$PREFIX/results/$RUN_KEY/"
# HF Jobs COMMAND... is a sequence of executable and arguments.
# Passing a long bash -lc string is unreliable; execute a mounted worker file.
hf jobs run --namespace adradar --name "storyforge-v02-r18-${STAGE}-no-train" \
  --flavor cpu-upgrade --timeout 90m \
  --env "STORYFORGE_R18_RUN_KEY=$RUN_KEY" \
  -v "$BUCKET:/workspace:rw" \
  "$IMAGE" bash /workspace/preflight/v02-r18/code/v02_r18_hf_worker.sh "$STAGE"
