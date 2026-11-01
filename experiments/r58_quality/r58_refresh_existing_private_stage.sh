#!/usr/bin/env bash
# R58: synchronize verified code into an existing PRIVATE A/B stage and test.
# No HF Jobs, tokenizer downloads, GPU inference or dataset mutation.
set -Eeuo pipefail
umask 077

BRANCH='r58/roleplay-sft-skill-v01'
MINIMUM_SHA='9a65db38dc7d8ddcd9e17c43f9e3e42fc45bbc47'
MODE="${1:---refresh-and-test}"
if [[ "$MODE" != '--refresh-and-test' && "$MODE" != '--synthetic-only' ]]; then
  printf 'Usage: %s [--refresh-and-test|--synthetic-only]\n' "$0" >&2
  exit 2
fi

REPO_ROOT="$(git rev-parse --show-toplevel)" || exit 42
cd "$REPO_ROOT"
if [[ "$(git branch --show-current)" != "$BRANCH" ]]; then
  echo 'HOLD: switch to the R58 branch before running this script' >&2
  exit 42
fi
if ! git merge-base --is-ancestor "$MINIMUM_SHA" HEAD; then
  echo 'HOLD: R58 branch does not contain the reviewed baseline' >&2
  exit 42
fi
if [[ -n "$(git status --porcelain)" ]]; then
  echo 'HOLD: working tree must be clean before code refresh' >&2
  exit 42
fi

export PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"
if [[ "$MODE" == '--refresh-and-test' ]]; then
  export R58_RUN_DIR="${R58_RUN_DIR:-$HOME/.local/share/storyforge/r58/r58-quality-pilot13-20261101T111719Z}"
  export R58_STAGE="${R58_STAGE:-$HOME/.local/share/storyforge/r58/r58-hf-gpu-dual-review-stage-20261101T114557Z}"
  export R58_REPO_ROOT="$PWD"

  python3 - <<'PY'
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

pilot = Path(os.environ["R58_RUN_DIR"])
stage = Path(os.environ["R58_STAGE"])
repo = Path(os.environ["R58_REPO_ROOT"])

def digest(path):
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("PRIVATE_FILE_MISSING_OR_SYMLINK")
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.digest()

def snapshot():
    files = [pilot / "owner_crosswalk.private.json"]
    for slot in ("A", "B"):
        files.extend((
            pilot / f"reviewer_{slot}.private.jsonl",
            stage / f"input_{slot}" / "source.private.jsonl",
        ))
        output = stage / f"output_{slot}"
        if output.is_symlink() or not output.is_dir():
            raise RuntimeError("PRIVATE_OUTPUT_INVALID")
        files.extend(sorted(p for p in output.rglob("*") if p.is_file() or p.is_symlink()))
    return {str(p): digest(p) for p in files}

try:
    before = snapshot()
    cmd = [
        sys.executable,
        "experiments/r58_quality/r58_hf_gpu_review_stage.py",
        "--pilot-dir", str(pilot),
        "--stage-dir", str(stage),
        "--repo-root", str(repo),
        "--refresh-code",
    ]
    counts = []
    for _ in range(2):
        completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            raise RuntimeError("STAGE_REFRESH_HOLD")
        result = json.loads(completed.stdout)
        if (result.get("status") != "R58_A_B_PRIVATE_CODE_REFRESHED__SOURCES_UNCHANGED"
                or result.get("slots") != 2
                or result.get("owner_crosswalk_uploaded") is not False
                or result.get("paid_gpu_submitted") is not False
                or result.get("private_text_emitted") is not False
                or result.get("training_authorized") is not False
                or type(result.get("code_files_updated")) is not int):
            raise RuntimeError("STAGE_REFRESH_RECEIPT_INVALID")
        counts.append(result["code_files_updated"])
    if counts[1] != 0:
        raise RuntimeError("STAGE_REFRESH_NOT_IDEMPOTENT")
    if before != snapshot():
        raise RuntimeError("PRIVATE_SOURCE_OR_OUTPUT_CHANGED")
    print(json.dumps({
        "status": "R58_PRIVATE_STAGE_CODE_REFRESH_PASS",
        "first_code_files_updated": counts[0],
        "second_code_files_updated": counts[1],
        "private_source_and_output_unchanged": True,
        "hf_job_submitted": False,
    }, sort_keys=True))
except Exception as exc:
    print("R58_PRIVATE_STAGE_REFRESH_HOLD: " + str(exc), file=sys.stderr)
    raise SystemExit(42)
PY
fi

python3 -m unittest discover -s tests -p 'test_token_preflight_core.py' -q
python3 -m unittest discover -s experiments/r58_quality -p 'test_r58_hf_*.py' -q
python3 -m unittest discover -s skills/storyforge-roleplay-sft/tests -p 'test_skill_token_reuse_contract.py' -q

if [[ "$MODE" == '--synthetic-only' ]]; then
  echo 'R58_SYNTHETIC_TESTS_PASS__NO_PRIVATE_STAGE_TOUCHED__NO_HF_JOB'
else
  echo 'R58_PRIVATE_STAGE_REFRESH_AND_SYNTHETIC_TESTS_PASS__NO_HF_JOB'
fi
