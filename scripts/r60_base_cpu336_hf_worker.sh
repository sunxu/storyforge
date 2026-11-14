#!/usr/bin/env bash
# R60 Base CPU336: CPU-only, private RO input and isolated RW SAFE receipt.
set -euo pipefail
umask 077
export CUDA_VISIBLE_DEVICES=""
export NVIDIA_VISIBLE_DEVICES="void"
export TOKENIZERS_PARALLELISM=false
export USE_HF=true
export PYTHONUNBUFFERED=1
export HF_HUB_DISABLE_TELEMETRY=1
KEY="${STORYFORGE_R60_WRAPCPU_KEY:-}"
[[ "$KEY" =~ ^r60-base-cpu336-[0-9]{8}T[0-9]{6}Z-[a-f0-9]{12}$ ]] || {
  echo R60_BASE_CPU336_KEY_HOLD >&2; exit 42;
}
ROOT=/input/common2
[[ -f "$ROOT/SHA256_MANIFEST_PRIVATE.json" && -d /output ]] || {
  echo R60_BASE_CPU336_STAGE_MISSING_HOLD >&2; exit 42;
}
SCRATCH="$(mktemp -d)"
chmod 700 "$SCRATCH"
trap 'rm -rf "$SCRATCH"' EXIT
if ! python -m pip install --disable-pip-version-check -q \
  -r "$ROOT/requirements/r60-common2-wrapped-cpu.in" \
  > "$SCRATCH/pip.log" 2>&1; then
  echo R60_BASE_CPU336_INSTALL_HOLD >&2; exit 42;
fi
# Preserve the already validated Common2 known decord metadata exception.
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
  echo R60_BASE_CPU336_DEPENDENCIES_HOLD >&2; exit 42;
}
export PYTHONPATH="$ROOT/src:$ROOT/scripts:$ROOT/experiments/r58_quality"
python "$ROOT/scripts/r60_base_cpu336_hf_worker.py" \
  --stage "$ROOT" --output /output --run-key "$KEY" \
  > "$SCRATCH/worker.log" 2>&1 || {
    echo R60_BASE_CPU336_WORKER_HOLD >&2; exit 42;
  }
# Only the already published SAFE aggregate can reach stdout.
python - <<'PY'
import json
from pathlib import Path
record = json.loads(Path("/output/R60_BASE_CPU336_HF_SAFE_RECEIPT.json").read_bytes())
assert record["status"] == "BASE_CPU336_ACTUAL_COLLATOR_PASS__ALL_HELD"
assert record["actual_collator_verified"] is True
assert record["train_admitted"] == 0 and record["gpu_started"] is False
print(json.dumps(record, sort_keys=True))
PY
