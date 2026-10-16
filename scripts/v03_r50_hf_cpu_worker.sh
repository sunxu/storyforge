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
  'transformers==5.16.1' 'huggingface_hub>=0.35,<3'
rev='1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0'
tokdir="/tmp/storyforge-tokenizer/$rev"
mkdir -p "$tokdir"
python - "$tokdir" "$rev" <<'PY'
from huggingface_hub import snapshot_download
import sys
snapshot_download(
    repo_id='Qwen/Qwen3.8-27B', revision=sys.argv[2], local_dir=sys.argv[1],
    allow_patterns=['tokenizer.json','tokenizer_config.json','special_tokens_map.json',
                    'added_tokens.json','chat_template.jinja','vocab.json','merges.txt'],
)
print('PINNED_TOKENIZER_FILES_READY__NO_MODEL_WEIGHTS')
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
