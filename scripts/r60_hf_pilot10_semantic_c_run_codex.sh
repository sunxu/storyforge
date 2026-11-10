#!/usr/bin/env bash
# Explicit user opt-in: sends ten PRIVATE blind histories/targets to Codex.
# No HF GPU jobs, no A/B results in prompts, ten fresh ephemeral sessions.
set -euo pipefail
set +x
umask 077

if [[ "$(printenv R60_C_ALLOW_CODEX_CLOUD || true)" != "YES" ]]; then
  echo "C_CODEX_CLOUD_CONSENT_REQUIRED: set R60_C_ALLOW_CODEX_CLOUD=YES explicitly." >&2
  exit 42
fi

REPO="$(cd "$(dirname "$0")/.." && pwd -P)"
cd "$REPO"
export PYTHONPATH="$REPO/src"
BASE="$HOME/.local/share/storyforge/r60/private"
AB="$BASE/hf-pilot10-owner-audit-20261108"
C_DIR="$BASE/hf-pilot10-c-blind-20261108"

[[ -d "$AB/A" && -d "$AB/B" && ! -L "$AB" ]]
[[ -d "$C_DIR" && ! -L "$C_DIR" ]]
[[ -f "$C_DIR/C_BLIND_PACKETS_PRIVATE.jsonl" ]]
[[ -f "$C_DIR/C_OWNER_MAP_PRIVATE.json" ]]
[[ -f "$C_DIR/C_PREPARE_SAFE.json" ]]
[[ ! -e "$C_DIR/C_CALIBRATION_SAFE.json" ]]
command -v codex >/dev/null

# Fresh Codex session per case, output-schema validation, private appends.
# Failure stops here: existing validated per-case results retained for resume.
if [[ -n "$(printenv R60_C_CODEX_MODEL || true)" ]]; then
  python3 -m storyforge_gold_quality.hf_pilot_semantic_c_codex \
    --c-dir "$C_DIR" --model "$R60_C_CODEX_MODEL"
else
  python3 -m storyforge_gold_quality.hf_pilot_semantic_c_codex \
    --c-dir "$C_DIR"
fi

# Reuse the exact existing local frozen Owner Stage for independent hash replay.
STAGE="$(printenv R60_HF_OWNER_STAGE_ROOT || true)"
if [[ -z "$STAGE" ]]; then
  STAGE="$(python3 - <<'PY'
import json
import sys
from pathlib import Path
from storyforge_gold_quality.hf_pilot_pairwise_audit import MODEL_PINS

base = Path.home() / ".local" / "share" / "storyforge"
matches = []
if base.is_dir():
    for crosswalk in base.rglob("owner_crosswalk.private.json"):
        if crosswalk.is_symlink() or crosswalk.parent.name != "owner":
            continue
        stage = crosswalk.parent.parent
        manifest = stage / "owner" / "stage_manifest.private.json"
        if (stage.is_symlink() or manifest.is_symlink() or not manifest.is_file()
                or not (stage / "input_A" / "source.private.jsonl").is_file()
                or not (stage / "input_B" / "source.private.jsonl").is_file()):
            continue
        try:
            meta = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if meta.get("count") == 1000 and meta.get("model_pins") == MODEL_PINS:
            matches.append(stage)
if len(matches) != 1:
    print("OWNER_STAGE_DISCOVERY_HOLD: set R60_HF_OWNER_STAGE_ROOT "
          "to the unique existing frozen Stage.", file=sys.stderr)
    sys.exit(42)
print(matches[0])
PY
)"
fi
[[ -d "$STAGE" && ! -L "$STAGE" ]]

python3 -m storyforge_gold_quality.hf_pilot_semantic_c reconcile \
  --stage-root "$STAGE" \
  --review-a-dir "$AB/A" \
  --review-b-dir "$AB/B" \
  --c-dir "$C_DIR" \
  --results "$C_DIR/C_RESULTS_PRIVATE.jsonl" \
  --safe-output "$C_DIR/C_CALIBRATION_SAFE.json"
