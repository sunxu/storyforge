#!/usr/bin/env bash
# R60 constructed-System: synthetic only, CPU-only and safe aggregate receipt.
set -euo pipefail
umask 077
export CUDA_VISIBLE_DEVICES=""
export NVIDIA_VISIBLE_DEVICES="void"
export TOKENIZERS_PARALLELISM=false
export USE_HF=true
export PYTHONUNBUFFERED=1
export HF_HUB_DISABLE_TELEMETRY=1
KEY="${STORYFORGE_R60_WRAPCPU_KEY:-}"
[[ "$KEY" =~ ^r60-constructcpu-[0-9]{8}T[0-9]{6}Z-[a-f0-9]{12}$ ]] || {
  echo R60_CONSTRUCTED_KEY_HOLD >&2; exit 42;
}
ROOT=/input/common2
[[ -f "$ROOT/SHA256_MANIFEST_PRIVATE.json" && -d /output ]] || {
  echo R60_CONSTRUCTED_MOUNT_HOLD >&2; exit 42;
}
SCRATCH="$(mktemp -d)"
chmod 700 "$SCRATCH"
trap 'rm -rf "$SCRATCH"' EXIT
if ! python -m pip install --disable-pip-version-check -q \
  -r "$ROOT/requirements/r60-common2-wrapped-cpu.in" \
  > "$SCRATCH/pip.log" 2>&1; then
  echo R60_CONSTRUCTED_INSTALL_HOLD >&2; exit 42;
fi
python - <<'PY' > "$SCRATCH/deps.log" 2>&1 || {
import importlib.metadata
import subprocess
import sys
c = subprocess.run([sys.executable, "-m", "pip", "check"],
                   capture_output=True, text=True, check=False)
lines = [x.strip() for x in c.stdout.splitlines() if x.strip()]
if not ((c.returncode == 0 and not lines and not c.stderr.strip()) or
        (c.returncode == 1 and
         lines == ["decord 0.6.0 is not supported on this platform"] and
         not c.stderr.strip())):
    raise SystemExit(42)
import decord
assert importlib.metadata.version("decord") == "0.6.0"
assert decord.cpu(0) is not None
import jinja2
assert jinja2.__version__ == "3.1.6"
PY
  echo R60_CONSTRUCTED_DEPENDENCIES_HOLD >&2; exit 42;
}
export PYTHONPATH="$ROOT/src:$ROOT/scripts:$ROOT/experiments/r58_quality"
python "$ROOT/scripts/r60_base_constructed_hf_cpu_worker.py" \
  --stage "$ROOT" --output /output --run-key "$KEY" \
  > "$SCRATCH/worker.log" 2>&1 || {
    echo R60_CONSTRUCTED_WORKER_HOLD >&2; exit 42;
  }
python - <<'PY'
import json
from pathlib import Path
r = json.loads(Path("/output/R60_BASE_CONSTRUCTED_HF_CPU_SAFE_RECEIPT.json").read_bytes())
assert r["status"] == "BASE_CONSTRUCTED_HF_CPU3_ACTUAL_COLLATOR_PASS__TRAIN_HOLD"
assert r["actual_collator_verified"] is True
assert r["train_admitted"] == 0 and r["gpu_started"] is False
assert r["synthetic_cases"] == 3
print(json.dumps(r, sort_keys=True))
PY
