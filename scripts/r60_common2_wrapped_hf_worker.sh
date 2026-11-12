#!/usr/bin/env bash
# Stage-specific wrapper around the existing ms-swift business auditor.
# This MUST execute on HF cpu-upgrade; NEVER on the Mac.
set -euo pipefail
umask 077
export CUDA_VISIBLE_DEVICES=""
export NVIDIA_VISIBLE_DEVICES="void"
export USE_HF=true
export TOKENIZERS_PARALLELISM=false
export PYTHONUNBUFFERED=1
export HF_HUB_DISABLE_TELEMETRY=1
KEY="${STORYFORGE_R60_WRAPCPU_KEY:-}"
[[ "$KEY" =~ ^r60-common2-wrapcpu-[0-9]{8}T[0-9]{6}Z-[a-f0-9]{12}$ ]] || {
  echo R60_WRAPPED_CPU_KEY_HOLD >&2; exit 42;
}
[[ -f /input/common2/SHA256_MANIFEST_PRIVATE.json && -d /output ]] || {
  echo R60_WRAPPED_CPU_MOUNT_HOLD >&2; exit 42;
}
export PYTHONPATH="/input/common2/src:/input/common2/scripts:/input/common2/experiments/r58_quality"
SCRATCH="$(mktemp -d)"
chmod 700 "$SCRATCH"
trap 'rm -rf "$SCRATCH"' EXIT

# Pin the successful Common2 CPU2 runtime; do not install model weights.
# Captured logs MUST NOT be copied to HF stdout or public Git.
if ! python -m pip install --disable-pip-version-check -q \
  'ms-swift==4.5.3' 'transformers==5.16.1' 'tokenizers==0.23.3' \
  'huggingface_hub==1.33.0' 'qwen-vl-utils==0.0.14' \
  'decord==0.6.0' 'torchvision==0.21.0' 'jinja2==3.1.6' \
  > "$SCRATCH/pip.log" 2>&1; then
  echo R60_WRAPPED_CPU_INSTALL_HOLD >&2
  exit 42
fi

# Exact known exception is permitted only when decord's CPU import works.
python - <<'PY' > "$SCRATCH/deps.log" 2>&1 || {
import importlib.metadata
import subprocess
import sys
c = subprocess.run([sys.executable, "-m", "pip", "check"],
                   capture_output=True, text=True, check=False)
lines = [x.strip() for x in c.stdout.splitlines() if x.strip()]
if not ((c.returncode == 0 and not lines and not c.stderr.strip())
        or (c.returncode == 1 and lines == ["decord 0.6.0 is not supported on this platform"]
            and not c.stderr.strip())):
    raise SystemExit(42)
import decord
assert importlib.metadata.version("decord") == "0.6.0"
assert decord.cpu(0) is not None
import jinja2
assert jinja2.__version__ == "3.1.6"
PY
  echo R60_WRAPPED_CPU_DEPENDENCIES_HOLD >&2
  exit 42
}

# Only the SAFE JSON is allowed to reach stdout; suppress all worker diagnostics.
python /input/common2/scripts/r60_common2_wrapped_hf_worker.py \
  --stage /input/common2 --output /output --run-key "$KEY" \
  > "$SCRATCH/worker.log" 2>&1 || {
    echo R60_WRAPPED_CPU_WORKER_HOLD >&2
    exit 42
  }
python - <<'PY'
import json
from pathlib import Path
p = Path("/output/R60_COMMON2_WRAPPED_CPU_SAFE_RECEIPT.json")
data = json.loads(p.read_bytes())
assert data["status"] == "R60_COMMON2_WRAPPED_HF_CPU_COLLATOR_PASS__TRAIN_HOLD"
assert data["train_admitted"] == 0 and data["gpu_started"] is False
assert data["actual_swift_collator_verified"] is True
print(json.dumps(data, sort_keys=True))
PY
