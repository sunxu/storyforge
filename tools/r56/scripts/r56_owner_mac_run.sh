#!/usr/bin/env bash
# Local only, CPU only; never runs HF/model scripts. Usage:
# bash scripts/r56_owner_mac_run.sh [repo_path] [unique_output_root]
set -euo pipefail
umask 077
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="${1:-$HOME/workspace/storyforge}"
OUT="${2:-$HOME/.local/share/storyforge/r56/owner-real-gold195-$(date -u +%Y%m%dT%H%M%SZ)}"
KIT="$ROOT/input/StoryForge_R56_Gold195_Screening_NoGPU_20261022.zip"
if [[ ! -f "$KIT" ]]; then echo 'BLOCK: missing original screening ZIP' >&2; exit 2; fi
if [[ -e "$OUT" ]]; then echo 'BLOCK: output dir exists; no overwrite' >&2; exit 2; fi
if ! git -C "$REPO" rev-parse --is-inside-work-tree >/dev/null 2>&1; then echo 'BLOCK: repository not found' >&2; exit 2; fi
# Does not checkout branches or pull automatically: no mutations of source repo.
# Requires the 5 exact frozen blobs; on a newer main revision the script still fails closed if changed.
mkdir -p "$OUT"
export R56_REPO="$REPO" R56_OUT="$OUT" R56_KIT="$KIT" R56_ROOT="$ROOT"
python3 - <<'PY'
import hashlib,json,os,pathlib,zipfile
out=pathlib.Path(os.environ['R56_OUT']); src=pathlib.Path(os.environ['R56_KIT']); dest=out/'toolkit'
assert hashlib.sha256(src.read_bytes()).hexdigest()=='630d5901aec9a27faa3036c74267f4183adc795b49230137ad3459098faad31c','R56 kit hash mismatch'
with zipfile.ZipFile(src) as z:
 for item in z.infolist():
  p=pathlib.PurePosixPath(item.filename)
  assert not p.is_absolute() and '..' not in p.parts
  assert ((item.external_attr >> 16) & 0o170000)!=0o120000,'SYMLINK_ZIP_ENTRY'
 z.extractall(dest)
 checks=json.loads((dest/'SHA256SUMS.json').read_text())['members']
 for name,h in checks.items():
  assert hashlib.sha256((dest/name).read_bytes()).hexdigest()==h,name
print('R56_TOOLKIT_SHA256_PASS')
PY
python3 -m unittest discover -s "$OUT/toolkit/tests" -p 'test_*.py' -v 2>"$OUT/ORIGINAL_11_TESTS.log"
python3 "$ROOT/tests/test_r56_deep_preflight.py" 2>"$OUT/NEW_TESTS.log"
python3 "$OUT/toolkit/scripts/r56_gold195_screen.py" \
  --repo "$REPO" \
  --historical "$OUT/toolkit/private/R56_HISTORICAL_EXPOSURE_WORLD_IDS_PRIVATE.json" \
  --out-dir "$OUT/original_prescreen" >"$OUT/original_run.log"
python3 "$ROOT/scripts/r56_deep_preflight.py" \
  --repo "$REPO" \
  --selection "$OUT/toolkit/private/R56_PROPOSED24_SOURCE_ID_ONLY_PRIVATE.json" \
  --eligibility "$OUT/toolkit/safe/R56_GOLD195_PRELIMINARY_ELIGIBILITY_AUDIT_20261022.json" \
  --out-dir "$OUT/deep_preflight" >"$OUT/deep_run.log"
python3 - <<'PY'
import hashlib,json,os,pathlib
out=pathlib.Path(os.environ['R56_OUT']);a=json.loads((out/'original_prescreen/R56_GOLD195_ELIGIBILITY_AUDIT.json').read_text());
checks={'gold_total':195,'gold87':87,'gold108':108,'historical_uuid_overlap_rows':163,'no_known_uuid_overlap_rows':32,'provisional_selected':24,'provisional_worlds':2,'formally_admitted_independent_test_rows':0}
for key,val in checks.items():assert a.get(key)==val,(key,a.get(key),val)
raw=json.loads((out/'deep_preflight/safe/R56_DEEP_PREFLIGHT_COUNTS_ONLY.json').read_text());assert raw['official_test_admitted']==0
import subprocess
head=subprocess.run(['git','-C',os.environ['R56_REPO'],'rev-parse','HEAD'],capture_output=True,text=True,check=True).stdout.strip()
receipt={'schema':'storyforge-r56-owner-local-CPU-actual-repo-receipt-v1','result':'LOCAL_R56_REAL_GOLD195_PRESCREEN_PASS__ALL24_HOLD','repo_head':head,'source':'five exact frozen Git blob SHA1, private frozen historical manifest and owner real repo','old_unit_tests':11,'r50_read':False,'gpu_job_started':False,'training_performed':False,'model_promoted':False,'official_test_admitted':0,
  'safe_summary_sha256':hashlib.sha256((out/'original_prescreen/R56_GOLD195_ELIGIBILITY_AUDIT.json').read_bytes()).hexdigest(),
  'deep_count_only_sha256':hashlib.sha256((out/'deep_preflight/safe/R56_DEEP_PREFLIGHT_COUNTS_ONLY.json').read_bytes()).hexdigest()}
(out/'R56_OWNER_CPU_RECEIPT_SAFE.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
print(receipt['result']);print('SAFE: '+str(out/'R56_OWNER_CPU_RECEIPT_SAFE.json'));print('PRIVATE GATE SHEETS: '+str(out/'deep_preflight/private'))
PY
