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
# Static regression against the missing-Jinja2 failure seen in CPU Job 6ad1e135... .
# The actual install-and-import smoke runs inside the HF worker before downloads.
grep -Fq "'jinja2==3.1.6'" "$worker" || { echo 'MISSING_PINNED_JINJA2_DEPENDENCY' >&2; exit 3; }
grep -Fq 'R50_JINJA_TEMPLATE_SELFTEST_PASS' "$worker" || { echo 'MISSING_JINJA_RUNTIME_SELFTEST' >&2; exit 3; }
# Prevent regressions that call the failing pinned-revision model metadata API.
grep -Fq 'R50_QWEN_DEFAULT_METADATA_SHA_PASS' "$worker" || { echo 'MISSING_MODEL_SHA_GUARD' >&2; exit 3; }
grep -Fq 'TOKENIZER_FILE_COMMIT_MISMATCH' "$worker" || { echo 'MISSING_PER_FILE_SHA_GUARD' >&2; exit 3; }
if grep -Fq "snapshot_download(" "$worker"; then
  echo 'REVISION_API_BUG_PRONE_SNAPSHOT_DOWNLOAD' >&2
  exit 3
fi
grep -Fq 'verify_model_revision' "$launcher" || { echo 'MISSING_NO_BILL_MODEL_PROBE' >&2; exit 3; }
# Cross-check the SAME exact 40-hex revision in worker, free API probe,
# and immutable 46-case preflight code BEFORE staging or paid CPU submission.
# Also simulate the incorrect prior worker SHA to ensure this guard catches it.
python3 - "$worker" "$launcher" "$(dirname "$launcher")/v03_r50_cpu_tokenizer_preflight_46.py" <<'PY'
import ast
import pathlib
import re
import sys

worker_path, launcher_path, preflight_path = map(pathlib.Path, sys.argv[1:])
w, l, p = (path.read_text(encoding='utf-8') for path in
           (worker_path, launcher_path, preflight_path))
frozen = '1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0'

def unique(pattern, source, label):
    vals = re.findall(pattern, source, re.M)
    if len(vals) != 1:
        raise SystemExit(f'R50_REVISION_PIN_HOLD: {label} has {len(vals)} pins')
    return vals[0]

worker_pin = unique(r"^rev='([0-9a-f]+)'$", w, 'worker')
launcher_pin = unique(r"^pin = '([0-9a-f]+)'$", l, 'launcher')
tree = ast.parse(p)
pin_values = [
    node.value.value
    for node in tree.body
    if isinstance(node, ast.Assign)
    and any(isinstance(target, ast.Name) and target.id == 'PINNED_REVISION'
            for target in node.targets)
    and isinstance(node.value, ast.Constant)
    and isinstance(node.value.value, str)
]
if len(pin_values) != 1:
    raise SystemExit('R50_REVISION_PIN_HOLD: preflight PINNED_REVISION missing')
preflight_pin = pin_values[0]
if not all(len(value) == 40 and value == frozen for value in
           (worker_pin, launcher_pin, preflight_pin)):
    raise SystemExit('R50_REVISION_PIN_HOLD: worker/launcher/preflight SHA mismatch')
# Negative regression: the exact SHA from the failed CPU Job must be rejected.
wrong = '1d4bf0f2ff6012fd82039d0dd7c60c0'
if wrong == frozen or unique(r"^rev='([0-9a-f]+)'$",
      w.replace("rev='" + frozen + "'", "rev='" + wrong + "'"),
      'mutated-worker') == frozen:
    raise SystemExit('R50_REVISION_PIN_NEGATIVE_TEST_HOLD')
print('R50_PINNED_REVISION_TRIPLE_MATCH_PASS', frozen)
PY
# Run pure-stdlib regression tests for the actual Transformers v5
# BatchEncoding/dict input_ids API before staging or paid CPU execution.
python3 "$(dirname "$launcher")/../tests/test_v03_r50_cpu_tokenizer_encoding.py"
# Protect against the old launcher re-staging a 2026-10-16 preflight
# from the obsolete 61f317b commit. All staged preflights must match the
# reviewed Git blob SHA, and submit must verify staged bytes before billing.
grep -Fq 'PINNED_PREFLIGHT_BLOB_SHA="c546194bd02608e921d9c673fa3e549c022468ae"' "$launcher" || {
  echo 'MISSING_PINNED_PREFLIGHT_BLOB_SHA' >&2; exit 3;
}
grep -Fq 'STAGED_PREFLIGHT_BLOB_SHA256_PASS__TRANSFORMERS_V5' "$launcher" || {
  echo 'MISSING_STAGED_PREFLIGHT_CHECK' >&2; exit 3;
}
if grep -Fq 'PINNED_PREFLIGHT_COMMIT=' "$launcher"; then
  echo 'OBSOLETE_PREFLIGHT_COMMIT_PIN' >&2; exit 3;
fi
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
