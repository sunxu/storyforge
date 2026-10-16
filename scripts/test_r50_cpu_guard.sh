#!/usr/bin/env bash
# Fail-closed local CPU-only guard checks; no HF calls, GPU, data or installs.
set -euo pipefail
worker="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/v03_r50_hf_cpu_worker.sh}"
[[ -f "$worker" ]] || { echo 'MISSING_CPU_WORKER' >&2; exit 2; }
# Regression: the Git-native launcher must point at the exact committed worker,
# not at the pre-rename r50_hf_cpu_worker.sh path.
launcher="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/v03_r50_hf_cpu_submit.sh"
[[ -f "$launcher" ]] || { echo 'MISSING_CPU_LAUNCHER' >&2; exit 2; }
if grep -Fq '$HERE/r50_hf_cpu_worker.sh' "$launcher"; then
  echo 'STALE_WORKER_PATH_IN_LAUNCHER' >&2
  exit 3
fi
grep -Fq '$HERE/v03_r50_hf_cpu_worker.sh' "$launcher" || {
  echo 'EXPECTED_WORKER_PATH_NOT_IN_LAUNCHER' >&2
  exit 3
}
for value in '' none cpu; do
  ACCELERATOR="$value" R50_WORKER_GUARD_TEST_ONLY=1 bash "$worker" >/dev/null
done
(env -u ACCELERATOR R50_WORKER_GUARD_TEST_ONLY=1 bash "$worker" >/dev/null)
for value in a100-large t4-medium a10g-small cuda gpu cpu-gpu; do
  if ACCELERATOR="$value" R50_WORKER_GUARD_TEST_ONLY=1 bash "$worker" >/dev/null 2>&1; then
    echo "CPU_GUARD_TEST_FAILED: erroneously accepted $value" >&2
    exit 3
  fi
done
printf '%s\n' 'R50_CPU_ONLY_GUARD_TEST_PASS: cpu/none/empty/unset accepted; GPU and unknown values rejected'
