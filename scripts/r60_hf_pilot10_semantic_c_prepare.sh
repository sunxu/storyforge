#!/usr/bin/env bash
# Owner Mac: prepare ten reviewer-C blind packets from already audited 5+5.
# No GPU, no model calls, no writes to stage or existing checkpoints.
set -euo pipefail
set +x
umask 077
REPO="$(cd "$(dirname "$0")/.." && pwd -P)"
cd "$REPO"
export PYTHONPATH="$REPO/src"
BASE="$HOME/.local/share/storyforge/r60/private"
AB="$BASE/hf-pilot10-owner-audit-20261108"
OUT="$BASE/hf-pilot10-c-blind-20261108"
[[ -d "$AB/A" && -d "$AB/B" && ! -L "$AB" ]]
[[ -f "$AB/R60_OWNER_PAIRWISE_PILOT10_SAFE.json" ]]
[[ ! -e "$OUT" && ! -L "$OUT" ]]

STAGE="${R60_HF_OWNER_STAGE_ROOT:-}"
if [[ -z "$STAGE" ]]; then
  STAGE="$(python3 - <<'PY'
import json
import sys
from pathlib import Path
from storyforge_gold_quality.hf_pilot_pairwise_audit import MODEL_PINS

base = Path.home() / ".local" / "share" / "storyforge"
candidates = []
if base.is_dir():
    for owner_map in base.rglob("owner_crosswalk.private.json"):
        if owner_map.is_symlink() or owner_map.parent.name != "owner":
            continue
        stage = owner_map.parent.parent
        manifest = stage / "owner" / "stage_manifest.private.json"
        if (stage.is_symlink() or not manifest.is_file() or manifest.is_symlink()
                or not (stage / "input_A" / "source.private.jsonl").is_file()
                or not (stage / "input_B" / "source.private.jsonl").is_file()):
            continue
        try:
            meta = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if meta.get("count") == 1000 and meta.get("model_pins") == MODEL_PINS:
            candidates.append(stage)
if len(candidates) != 1:
    print("OWNER_STAGE_DISCOVERY_HOLD: expected exactly one 1000-case stage; "
          "set R60_HF_OWNER_STAGE_ROOT to the existing Stage root.", file=sys.stderr)
    sys.exit(42)
print(candidates[0])
PY
)"
fi
[[ -d "$STAGE" && ! -L "$STAGE" ]]
[[ -f "$STAGE/owner/owner_crosswalk.private.json" ]]
[[ -f "$STAGE/owner/stage_manifest.private.json" ]]
python3 -m storyforge_gold_quality.hf_pilot_semantic_c prepare \
  --stage-root "$STAGE" \
  --review-a-dir "$AB/A" \
  --review-b-dir "$AB/B" \
  --c-dir "$OUT"
