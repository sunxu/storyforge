#!/usr/bin/env bash
# HF remote CPU-only tokenizer worker. No model inference or weights downloaded.
set -euo pipefail
umask 077
# CPU-only ACCELERATOR representations seen across HF documentation and
# actual StoryForge HF CPU Job logs: empty, none, cpu.
# Keep all other values fail-closed (including GPU hardware names).
accelerator="${ACCELERATOR:-}"
case "$accelerator" in
  ""|none|cpu) ;;
  *) echo "GPU_FLAVOR_FORBIDDEN: accelerator=$accelerator" >&2; exit 3 ;;
esac
echo "CPU_ONLY_GUARD_PASS: accelerator=${accelerator:-<empty>} cpu_cores=${CPU_CORES:-unknown} job_id=${JOB_ID:-unknown}"
# Local-only guard self-test. This exits before any private data, bucket,
# package install, tokenizer download, or paid inference is touched.
if [[ "${R50_WORKER_GUARD_TEST_ONLY:-}" == "1" ]]; then
  exit 0
fi
key="${R50_STAGE_KEY:?R50_STAGE_KEY must be provided by launcher}"
[[ "$key" =~ ^r50-token-[0-9]{8}T[0-9]{6}Z-[a-f0-9]{8}$ ]] || { echo INVALID_RUN_KEY >&2; exit 2; }
base="/workspace/preflight/v03-r50/cpu-tokenizer/$key"
mkdir -p "$base/reports"
python -m pip install --disable-pip-version-check --quiet \
  'transformers==5.16.1' 'huggingface_hub>=0.35,<3' 'jinja2==3.1.6'
# Fail before model/tokenizer download if the chat-template dependency is missing.
python - <<'PY'
from importlib.metadata import version
from jinja2 import Environment
from transformers import AutoTokenizer  # import only: no model or weights
assert Environment().from_string('{{ value }}').render(value='ok') == 'ok'
assert version('jinja2') == '3.1.6'
print('R50_JINJA_TEMPLATE_SELFTEST_PASS: jinja2=3.1.6; tokenizer-only mode')
PY
rev='1d4bf0f2ff6012fd82039d0dd7c60c0'
tokdir="/tmp/storyforge-tokenizer/$rev"
mkdir -p "$tokdir"
python - "$tokdir" "$rev" <<'PY'
# The immutable commit exists on the Hub, but the explicit
# /api/models/<repo>/revision/<commit> API returned 404 in the CPU Job.
# Bypass only THAT metadata endpoint. Verify public HEAD SHA before and after;
# verify the actual immutable revision reported for EVERY downloaded file.
from huggingface_hub import HfApi, hf_hub_download
from pathlib import Path
import shutil
import sys

target = Path(sys.argv[1])
pin = sys.argv[2]
repo = 'Qwen/Qwen3.8-27B'
api = HfApi()
head = api.model_info(repo_id=repo).sha
if head != pin:
    raise RuntimeError(f'QWEN_MAIN_SHA_MISMATCH: expected {pin}, received {head}')
print('R50_QWEN_DEFAULT_METADATA_SHA_PASS', head, flush=True)

# Fetch only the five known tokenizer files. Never fetch weights or config.json.
required = ('tokenizer.json', 'tokenizer_config.json', 'chat_template.jinja',
            'vocab.json', 'merges.txt')
target.mkdir(parents=True, exist_ok=True)
for name in required:
    downloaded = Path(hf_hub_download(repo_id=repo, filename=name, revision='main'))
    # hub cache paths contain snapshots/<actual Git commit>/<filename>.
    # This guarantees no silent fallback to a drifting main revision.
    if downloaded.parent.name != pin or downloaded.parent.parent.name != 'snapshots':
        raise RuntimeError(f'TOKENIZER_FILE_COMMIT_MISMATCH: {name}')
    shutil.copyfile(downloaded, target / name)
    print('R50_PINNED_TOKENIZER_FILE_PASS', name, flush=True)
if api.model_info(repo_id=repo).sha != pin:
    raise RuntimeError('QWEN_MAIN_SHA_CHANGED_DURING_DOWNLOAD')
print('PINNED_TOKENIZER_FILES_READY__NO_MODEL_WEIGHTS', flush=True)
PY
python -u "$base/code/preflight.py" \
  --candidates "$base/private/R50_CANDIDATE_46_PRESEAL_PRIVATE.jsonl" \
  --system-file "$base/private/R45_SYSTEM_CANDIDATE_64_OF_64_NOT_APPROVED_PRIVATE.txt" \
  --tokenizer-snapshot "$tokdir" \
  --thinking disabled \
  --max-context 16384 \
  --reserved-output-tokens 1536 \
  --output "$base/reports/R50_46_TOKENIZER.json"
echo "CPU_TOKENIZER_PREFLIGHT_DONE__NO_INFERENCE__NO_GPU__NO_FINAL_SEAL"
