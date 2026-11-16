#!/usr/bin/env bash
# R60 actual 293/43 release: CPU-only technical audit, no model weights.
set -euo pipefail
umask 077
export CUDA_VISIBLE_DEVICES=""
export NVIDIA_VISIBLE_DEVICES="void"
export TOKENIZERS_PARALLELISM=false
export USE_HF=true
export PYTHONUNBUFFERED=1
export HF_HUB_DISABLE_TELEMETRY=1
KEY="${STORYFORGE_R60_WRAPCPU_KEY:-}"
[[ "$KEY" =~ ^r60-base336-finalcpu-[0-9]{8}T[0-9]{6}Z-[a-f0-9]{12}$ ]] || {
  echo BASE336_FINAL_CPU_KEY_HOLD >&2; exit 42;
}
ROOT=/input/common2
[[ -f "$ROOT/SHA256_MANIFEST_PRIVATE.json" && -d /output ]] || {
  echo BASE336_FINAL_CPU_STAGE_HOLD >&2; exit 42;
}
SCRATCH="$(mktemp -d)"
chmod 700 "$SCRATCH"
trap 'rm -rf "$SCRATCH"' EXIT
if ! python -m pip install --disable-pip-version-check -q \
  -r "$ROOT/requirements/r60-common2-wrapped-cpu.in" \
  > "$SCRATCH/pip.log" 2>&1; then
  echo BASE336_FINAL_CPU_INSTALL_HOLD >&2; exit 42;
fi
python - <<'PY' > "$SCRATCH/deps.log" 2>&1 || {
import importlib.metadata
import subprocess
import sys
c = subprocess.run([sys.executable, "-m", "pip", "check"],
                   capture_output=True, text=True, check=False)
lines = [x.strip() for x in c.stdout.splitlines() if x.strip()]
if not ((c.returncode == 0 and not lines and not c.stderr.strip())
        or (c.returncode == 1
            and lines == ["decord 0.6.0 is not supported on this platform"]
            and not c.stderr.strip())):
    raise SystemExit(42)
import decord
assert importlib.metadata.version("decord") == "0.6.0"
assert decord.cpu(0) is not None
import jinja2
assert jinja2.__version__ == "3.1.6"
PY
  echo BASE336_FINAL_CPU_DEPS_HOLD >&2; exit 42;
}
export PYTHONPATH="$ROOT/src:$ROOT/scripts:$ROOT/experiments/r58_quality"
python "$ROOT/scripts/r60_base336_final_cpu_worker.py" \
  --stage "$ROOT" --output /output --run-key "$KEY" \
  > "$SCRATCH/worker.log" 2>&1 || {
    echo BASE336_FINAL_CPU_WORKER_HOLD >&2; exit 42;
  }
python - <<'PY'
import json
from pathlib import Path
p = Path("/output/R60_BASE336_FINAL_CPU_SAFE_RECEIPT.json")
record = json.loads(p.read_bytes())
assert record["status"] == "BASE336_FINAL_CPU_ACTUAL_COLLATOR_PASS__GPU_HOLD"
assert record["actual_collator_verified"] is True
assert record["last_assistant_label_mask_verified"] is True
assert record["train_admitted"] == 0 and record["gpu_started"] is False
print(json.dumps(record, sort_keys=True))
PY
