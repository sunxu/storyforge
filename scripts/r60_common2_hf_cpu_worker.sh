#!/usr/bin/env bash
# R60 Common2: isolated PAID HF CPU-only REAL ms-swift audit, NEVER train.
set -euo pipefail
umask 077
KEY="${STORYFORGE_R60_COMMON2_RUN_KEY:?RUN_KEY_REQUIRED}"
[[ "$KEY" =~ ^r60-common2-cpu2-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{12}$ ]] || {
  echo R60_COMMON2_RUN_KEY_HOLD >&2; exit 42;
}
BASE=/workspace/preflight/r60/common2/cpu2
ROOT="$BASE/runs/$KEY"
CODE="$ROOT/code"
OUT="$BASE/results/$KEY"
cd "$ROOT"
sha256sum --check --status SHA256SUMS.txt || {
  echo R60_COMMON2_STAGE_SHA_HOLD >&2; exit 42;
}
[[ -s "$CODE/scripts/hf_label_mask_audit.py" &&
   -s "$CODE/experiments/r58_quality/r60_common2_sft_cpu_template_audit.py" &&
   -s "$ROOT/private_stage/R60_COMMON2_SFT_EXPERIMENTAL_NOT_ADMITTED_PRIVATE.jsonl" ]] || {
  echo R60_COMMON2_SOURCE_MISSING_HOLD >&2; exit 42;
}
export CUDA_VISIBLE_DEVICES=""
export HF_HUB_OFFLINE=0
export TRANSFORMERS_OFFLINE=0
export PYTHONUNBUFFERED=1
export TOKENIZERS_PARALLELISM=false
export PYTHONPATH="$CODE/experiments/r58_quality:$CODE/scripts"
# Same verified R53 runtime pin; CPU flavor explicitly selected at submit gate.
python -m pip install --disable-pip-version-check \
 'ms-swift==4.5.3' 'transformers==5.16.1' \
 'huggingface_hub>=0.35,<3' 'qwen-vl-utils>=0.0.14'
SNAP="$BASE/tokenizer/snapshots/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0"
export SNAP
python - <<'PY'
import os
from pathlib import Path
from huggingface_hub import snapshot_download
revision = "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0"
target = Path(os.environ["SNAP"])
target.mkdir(mode=0o700, parents=True, exist_ok=True)
snapshot_download(
    repo_id="Qwen/Qwen3.8-27B", revision=revision, local_dir=str(target),
    allow_patterns=[
        "config.json", "tokenizer.json", "tokenizer_config.json",
        "chat_template.jinja", "vocab.json", "merges.txt",
        "preprocessor_config.json", "video_preprocessor_config.json",
        "generation_config.json",
    ],
)
assert all((target / x).is_file() for x in (
    "tokenizer.json", "tokenizer_config.json", "config.json"))
print("R60_COMMON2_PINNED_TOKENIZER_FILES_READY", flush=True)
PY
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
mkdir -p "$OUT"
cd "$CODE"
python -u "$CODE/experiments/r58_quality/r60_common2_sft_cpu_template_audit.py" \
 --input-dir "$ROOT/private_stage" --snapshot "$SNAP" --stage both \
 > "$OUT/R60_COMMON2_CPU2_SAFE_RECEIPT.json" || {
  echo R60_COMMON2_CPU2_RUNTIME_HOLD >&2; exit 42;
}
python - "$OUT/R60_COMMON2_CPU2_SAFE_RECEIPT.json" <<'PY'
import json, sys
from pathlib import Path
r = json.loads(Path(sys.argv[1]).read_text())
if (r.get("status") != "COMMON2_CPU_TOKENIZER_COLLATOR_PASS__R50_TRAIN_HOLD"
        or r.get("cases") != 2 or r.get("collator_verified") is not True
        or r.get("r50_complete_exclusion_verified") is not False
        or r.get("train_admitted") != 0):
    raise SystemExit("R60_COMMON2_CPU2_RECEIPT_HOLD")
print("R60_COMMON2_HF_CPU2_REAL_COLLATOR_PASS__TRAIN_HOLD", flush=True)
PY
