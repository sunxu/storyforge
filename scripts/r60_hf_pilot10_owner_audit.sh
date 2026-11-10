#!/usr/bin/env bash
# Owner Mac only: read-only frozen A/B pilot audit, no GPU, no source writes.
set -euo pipefail
set +x
umask 077

REPO="$(cd "$(dirname "$0")/.." && pwd -P)"
cd "$REPO"
ROOT="hf://buckets/adradar/storyforge-training/quality-review/r60/r60-quality-cpu-20261108T082545Z"
BASE="$HOME/.local/share/storyforge/r60/private"
OUT="$BASE/hf-pilot10-owner-audit-20261108"
export PYTHONPATH="$REPO/src"

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
    print("OWNER_STAGE_DISCOVERY_HOLD: expected exactly one matching local 1000-case stage; "
          "set R60_HF_OWNER_STAGE_ROOT to the existing stage root.", file=sys.stderr)
    sys.exit(42)
print(candidates[0])
PY
)"
fi

[[ -d "$STAGE" && ! -L "$STAGE" ]]
[[ -f "$STAGE/owner/owner_crosswalk.private.json" ]]
[[ -f "$STAGE/owner/stage_manifest.private.json" ]]
[[ -f "$STAGE/input_A/source.private.jsonl" ]]
[[ -f "$STAGE/input_B/source.private.jsonl" ]]
[[ -d "$BASE" && ! -L "$BASE" ]]
[[ ! -e "$OUT" && ! -L "$OUT" ]]
mkdir -m 700 "$OUT"
mkdir -m 700 "$OUT/A" "$OUT/B"

for i in 1 2 3 4 5; do
  filename="$(printf 'review_%04d.private.json' "$i")"
  hf buckets cp "$ROOT/gpu-review-output-A-pilot5-v2-01/$filename" "$OUT/A/$filename"
  hf buckets cp "$ROOT/gpu-review-output-B-pilot5-v3-01/$filename" "$OUT/B/$filename"
done
chmod 600 "$OUT"/A/*.json "$OUT"/B/*.json
python3 -m storyforge_gold_quality.hf_pilot_pairwise_audit \
  --stage-root "$STAGE" \
  --review-a-dir "$OUT/A" \
  --review-b-dir "$OUT/B" \
  --safe-output "$OUT/R60_OWNER_PAIRWISE_PILOT10_SAFE.json"
