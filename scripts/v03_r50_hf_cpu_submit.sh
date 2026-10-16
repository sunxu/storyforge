#!/usr/bin/env bash
# StoryForge R50: Git-native, private-bucket HF CPU tokenizer check.
# stage-from-bucket: reuse ALREADY-STAGED private R50 input from HF Bucket.
# submit: explicitly authorized single paid cpu-basic Job, NO GPU.
set -euo pipefail
umask 077

MODE="${1:-}"
SOURCE_STAGE_KEY="${2:-}"
BUCKET="hf://buckets/adradar/storyforge-training"
PINNED_PREFLIGHT_COMMIT="61f317b123f1802b0ae6739f6244892c828c5cf5"
PINNED_CASE_SHA="109642a6c0e27895ae83274bec79ec9f53d922e407ca435431acf3f31a31e1f2"
PINNED_SYSTEM_SHA="5e1b28cd9181f5d334f1f10a54a251f9255e655a3e597519c7cfcc530d8c5e83"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${STORYFORGE_REPO:-$(cd "$HERE/.." && pwd)}"

need() { command -v "$1" >/dev/null || { echo "MISSING_COMMAND: $1" >&2; exit 2; }; }
check_key() {
  [[ "$1" =~ ^r50-token-[0-9]{8}T[0-9]{6}Z-[a-f0-9]{8}$ ]] || {
    echo 'INVALID_STAGE_KEY' >&2; exit 2;
  }
}
need hf
need python3

case "$MODE" in
  stage-from-bucket)
    check_key "$SOURCE_STAGE_KEY"
    need git
    [[ -e "$REPO/.git" ]] || { echo 'MISSING_LOCAL_GIT_REPO' >&2; exit 2; }
    [[ "$(git -C "$REPO" rev-parse "$PINNED_PREFLIGHT_COMMIT^{commit}")" == "$PINNED_PREFLIGHT_COMMIT" ]] || {
      echo 'PINNED_PREFLIGHT_COMMIT_NOT_FOUND' >&2; exit 2;
    }
    bash "$HERE/test_r50_cpu_guard.sh" "$HERE/v03_r50_hf_cpu_worker.sh"
    tmp="$(mktemp -d)"
    trap 'rm -rf "$tmp"' EXIT
    mkdir -p "$tmp/code" "$tmp/private"
    git -C "$REPO" show "$PINNED_PREFLIGHT_COMMIT:scripts/v03_r50_cpu_tokenizer_preflight_46.py" > "$tmp/code/preflight.py"
    cp "$HERE/v03_r50_hf_cpu_worker.sh" "$tmp/code/worker.sh"
    # The R50 private prompts stay OUTSIDE Git. Reuse previously staged HF inputs.
    for name in R50_CANDIDATE_46_PRESEAL_PRIVATE.jsonl R45_SYSTEM_CANDIDATE_64_OF_64_NOT_APPROVED_PRIVATE.txt; do
      hf buckets cp "$BUCKET/preflight/v03-r50/cpu-tokenizer/$SOURCE_STAGE_KEY/private/$name" "$tmp/private/$name"
    done
    python3 - "$tmp/private" "$PINNED_CASE_SHA" "$PINNED_SYSTEM_SHA" <<'PY'
import hashlib, pathlib, sys
folder = pathlib.Path(sys.argv[1])
checks = {
    'R50_CANDIDATE_46_PRESEAL_PRIVATE.jsonl': sys.argv[2],
    'R45_SYSTEM_CANDIDATE_64_OF_64_NOT_APPROVED_PRIVATE.txt': sys.argv[3],
}
for name, expected in checks.items():
    path = folder/name
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise SystemExit('PRIVATE_HF_STAGE_INPUT_SHA256_HOLD: '+name)
    path.chmod(0o600)
print('PRIVATE_HF_SOURCE_STAGE_SHA256_PASS')
PY
    key="r50-token-$(date -u +%Y%m%dT%H%M%SZ)-$(python3 - <<'PY'
import secrets
print(secrets.token_hex(4))
PY
)"
    stage="$BUCKET/preflight/v03-r50/cpu-tokenizer/$key"
    for folder in code private; do
      for path in "$tmp/$folder/"*; do
        hf buckets cp "$path" "$stage/$folder/$(basename "$path")"
      done
    done
    echo "R50_STAGE_KEY=$key"
    echo 'STAGED_FROM_EXISTING_PRIVATE_HF_BUCKET__NO_JOB_SUBMITTED'
    echo 'Explicit separate authorization required for a paid CPU run.'
    ;;
  submit)
    check_key "$SOURCE_STAGE_KEY"
    [[ "${STORYFORGE_ALLOW_PAID_CPU:-}" == YES && "${STORYFORGE_R50_CPU_JOB_ONLY:-}" == YES ]] || {
      echo 'PAID_CPU_NOT_AUTHORIZED' >&2; exit 3;
    }
    bash "$HERE/test_r50_cpu_guard.sh" "$HERE/v03_r50_hf_cpu_worker.sh"
    tmp="$(mktemp -d)"
    trap 'rm -rf "$tmp"' EXIT
    hf buckets cp "$BUCKET/preflight/v03-r50/cpu-tokenizer/$SOURCE_STAGE_KEY/code/worker.sh" "$tmp/staged_worker.sh"
    python3 - "$HERE/v03_r50_hf_cpu_worker.sh" "$tmp/staged_worker.sh" <<'PY'
import hashlib, pathlib, sys
sha = lambda p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
if sha(sys.argv[1]) != sha(sys.argv[2]):
    raise SystemExit('STAGED_WORKER_SHA_MISMATCH__NO_JOB_SUBMITTED')
print('STAGED_WORKER_SHA256_PASS__CPU_GUARD_V2')
PY
    echo "SUBMITTING_SINGLE_CPU_BASIC_JOB_FOR $SOURCE_STAGE_KEY"
    hf jobs run \
      --namespace adradar --name storyforge-r50-46-tokenizer-cpu \
      --flavor cpu-basic --timeout 30m \
      --env "R50_STAGE_KEY=$SOURCE_STAGE_KEY" \
      -v "$BUCKET:/workspace:rw" \
      python:3.12-slim \
      bash "/workspace/preflight/v03-r50/cpu-tokenizer/$SOURCE_STAGE_KEY/code/worker.sh"
    echo "REPORT_URI=$BUCKET/preflight/v03-r50/cpu-tokenizer/$SOURCE_STAGE_KEY/reports/R50_46_TOKENIZER.json"
    ;;
  *)
    echo 'Usage: bash scripts/v03_r50_hf_cpu_submit.sh stage-from-bucket <PRIOR_STAGE_KEY> | submit <NEW_STAGE_KEY>' >&2
    exit 2
    ;;
esac
