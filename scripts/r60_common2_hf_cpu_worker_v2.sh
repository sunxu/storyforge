#!/usr/bin/env bash
# R60 Common2 CPU2 v2: RO input, isolated RW SAFE output; no training/GPU.
# Intended for a NEW create-only SHA-bound stage, never the frozen 27-file stage.
set -euo pipefail
umask 077
export CUDA_VISIBLE_DEVICES=""
export TOKENIZERS_PARALLELISM=false
export USE_HF=true
export PYTHONUNBUFFERED=1

KEY="${STORYFORGE_R60_COMMON2_RUN_KEY:?RUN_KEY_REQUIRED}"
[[ "$KEY" =~ ^r60-common2-cpu2-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{12}$ ]] || {
  echo R60_CPU2_V2_RUN_KEY_HOLD >&2; exit 42;
}
ROOT="/input/common2"
CODE="$ROOT/code"
INPUT="$ROOT/private_stage"
OUT="/output"
[[ -f "$ROOT/SHA256SUMS.txt" && -f "$INPUT/R60_COMMON2_SFT_EXPERIMENTAL_NOT_ADMITTED_PRIVATE.jsonl" ]] || {
  echo R60_CPU2_V2_INPUT_MISSING_HOLD >&2; exit 42;
}
[[ -d "$OUT" && ! -L "$OUT" ]] || {
  echo R60_CPU2_V2_OUTPUT_MOUNT_HOLD >&2; exit 42;
}
(cd "$ROOT" && sha256sum --check --status SHA256SUMS.txt) || {
  echo R60_CPU2_V2_SHA_HOLD >&2; exit 42;
}
# Never change RO input. The existing audit validates local private mode bits.
SCRATCH="$(mktemp -d)"
chmod 700 "$SCRATCH"
PRIVATE_PARENT="$HOME/.local/share/storyforge/r60/private"
mkdir -p "$PRIVATE_PARENT"
chmod 700 "$PRIVATE_PARENT"
PRIVATE_INPUT="$PRIVATE_PARENT/$KEY"
mkdir -m 700 "$PRIVATE_INPUT" || { echo R60_CPU2_V2_PRIVATE_DIR_EXISTS_HOLD >&2; exit 42; }
trap 'rm -rf -- "$SCRATCH" "$PRIVATE_INPUT"' EXIT
cp -- "$INPUT/R60_COMMON2_SFT_EXPERIMENTAL_NOT_ADMITTED_PRIVATE.jsonl" "$PRIVATE_INPUT/"
cp -- "$INPUT/R60_COMMON2_SFT_EXPERIMENTAL_MANIFEST_PRIVATE.json" "$PRIVATE_INPUT/"
chmod 600 "$PRIVATE_INPUT/"*
SNAP="$SCRATCH/tokenizer/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0"
mkdir -p "$SNAP"

python -m pip install --disable-pip-version-check \
  'ms-swift==4.5.3' 'transformers==5.16.1' \
  'huggingface_hub>=0.35,<3' 'qwen-vl-utils>=0.0.14'
python -m pip check >/dev/null || { echo R60_CPU2_V2_DEPENDENCY_HOLD >&2; exit 42; }
export SNAP
python - <<'PY'
import os
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id="Qwen/Qwen3.8-27B",
    revision="1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0",
    local_dir=os.environ["SNAP"],
    allow_patterns=[
        "config.json", "tokenizer.json", "tokenizer_config.json",
        "chat_template.jinja", "vocab.json", "merges.txt",
        "preprocessor_config.json", "video_preprocessor_config.json",
        "generation_config.json",
    ],
)
PY
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export PYTHONPATH="$CODE/experiments/r58_quality:$CODE/scripts"
# Capture stdout to scratch, never stream private internals to logs.
python -u "$CODE/experiments/r58_quality/r60_common2_sft_cpu_template_audit.py" \
  --input-dir "$PRIVATE_INPUT" --snapshot "$SNAP" --stage both \
  > "$SCRATCH/receipt.json" || { echo R60_CPU2_V2_AUDIT_HOLD >&2; exit 42; }

# Strict schema and create-only SAFE publish. No final stdout of raw receipt.
export RECEIPT_SRC="$SCRATCH/receipt.json"
export RECEIPT_DST="$OUT/R60_COMMON2_CPU2_SAFE_RECEIPT.json"
python - <<'PY'
import json
import os
from pathlib import Path
r = json.loads(Path(os.environ["RECEIPT_SRC"]).read_bytes())
if not (r.get("status") == "COMMON2_CPU_TOKENIZER_COLLATOR_PASS__R50_TRAIN_HOLD"
        and r.get("cases") == 2
        and r.get("collator_verified") is True
        and r.get("r50_complete_exclusion_verified") is False
        and r.get("train_admitted") == 0
        and r.get("gpu_started") is False
        and r.get("private_values_emitted") is False):
    raise SystemExit("R60_CPU2_V2_RECEIPT_HOLD")
raw = json.dumps(r, sort_keys=True, separators=(",", ":")).encode() + b"\n"
if len(raw) > 8192:
    raise SystemExit("R60_CPU2_V2_RECEIPT_SIZE_HOLD")
fd = os.open(os.environ["RECEIPT_DST"], os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "wb") as f:
    f.write(raw)
    f.flush()
    os.fsync(f.fileno())
print("R60_CPU2_V2_REAL_COLLATOR_PASS__R50_TRAIN_HOLD")
PY
