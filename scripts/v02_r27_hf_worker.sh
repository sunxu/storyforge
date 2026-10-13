# StoryForge R27 diagnostic worker: no training; fail before dependency install on bad input.
set -euo pipefail
STAGE=${1:-both}
[[ "$STAGE" == both ]] || { echo 'Only actual ms-swift both-stage is permitted' >&2; exit 2; }
ROOT=/workspace/preflight/v02-r27
INPUT="$ROOT/private/r27_private_candidate_117_NOT_APPROVED.jsonl"
: "${STORYFORGE_R27_INPUT_SHA:?expected candidate hash required}"
: "${STORYFORGE_R27_RUN_KEY:?run key required}"
# Fail fast before pip install (CPU runtime is billable).
python - "$INPUT" "$STORYFORGE_R27_INPUT_SHA" <<'PY_SOURCE_GATE'
import hashlib, json, pathlib, sys
source = pathlib.Path(sys.argv[1])
expected = sys.argv[2]
if not source.is_file():
    raise SystemExit(f'R27_SOURCE_BLOCKED: required 117-row source missing: {source}')
blob = source.read_bytes()
actual = hashlib.sha256(blob).hexdigest()
if actual != expected:
    raise SystemExit(f'R27_SOURCE_BLOCKED: SHA256 mismatch: {actual}')
try:
    rows = [json.loads(line) for line in blob.splitlines() if line.strip()]
    if len(rows) != 117 or len({r['id'] for r in rows}) != 117:
        raise ValueError('expected exactly 117 distinct candidate IDs')
    if any(r['metadata']['dataset_admission'] != 'NOT_APPROVED' for r in rows):
        raise ValueError('unauthorized approval state')
except (ValueError, KeyError, TypeError) as exc:
    raise SystemExit(f'R27_SOURCE_BLOCKED: {exc}') from exc
print(f'R27_SOURCE_PREFLIGHT_PASS 117/117 sha256={actual}', flush=True)
PY_SOURCE_GATE
cd "$ROOT/code"
python -m pip install --disable-pip-version-check \
  'ms-swift==4.5.3' 'transformers==5.16.1' \
  'huggingface_hub>=0.35,<3' 'qwen-vl-utils>=0.0.14'
python -u "$ROOT/code/r27_hf_final_input_audit.py" \
  --input "$INPUT" \
  --expected-sha256 "$STORYFORGE_R27_INPUT_SHA" \
  --output-dir "$ROOT/results/$STORYFORGE_R27_RUN_KEY"
