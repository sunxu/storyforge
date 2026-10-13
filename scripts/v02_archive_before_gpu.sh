#!/usr/bin/env bash
# StoryForge v0.2 exact-hash backup of private R18/R26/R27 and original source.
# No training or Hugging Face job is launched.
set -euo pipefail

usage() {
  echo 'Usage: bash scripts/v02_archive_before_gpu.sh RAW_CHAT_ZIP R26_ZIP R27_HOTFIX_ZIP R18_REPORT_JSON [--push]' >&2
  exit 2
}
[[ $# -ge 4 && $# -le 5 ]] || usage
RAW=$1; R26=$2; R27=$3; R18=$4
ACTION=${5:-stage}
[[ "$ACTION" == stage || "$ACTION" == --push ]] || usage
for p in "$RAW" "$R26" "$R27" "$R18"; do
  [[ -s "$p" ]] || { echo "BLOCKED: required source missing: $p" >&2; exit 2; }
done
command -v git >/dev/null || { echo 'BLOCKED: git missing' >&2; exit 2; }
git lfs version >/dev/null 2>&1 || { echo 'BLOCKED: git-lfs missing (brew install git-lfs)' >&2; exit 2; }
REPO=$(git rev-parse --show-toplevel 2>/dev/null) || { echo 'BLOCKED: not in a Git checkout' >&2; exit 2; }
cd "$REPO"
[[ $(git branch --show-current) == main ]] || { echo 'BLOCKED: checkout main first' >&2; exit 2; }
[[ $(git remote get-url origin) == *sunxu/storyforge* ]] || { echo 'BLOCKED: incorrect remote' >&2; exit 2; }

BASE=evaluations/v0.2/training-readiness/20261013/private
FILES=(
  "$BASE/original_chat_jsonl_14_20261013.zip"
  "$BASE/R26_Source_Anchored_History_20261013.zip"
  "$BASE/R27_HF117_Fix_20261013.zip"
  "$BASE/R18_HF40_Actual_Collator_Report_20261013.json"
)
# Allow unrelated staged, unstaged, and untracked work: this script never touches it.
# Before pushing, ensure the existing HEAD has no unrelated local commits.
if [[ "$ACTION" == --push ]]; then
  git fetch origin main --quiet
  [[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || {
    echo "BLOCKED: local main differs from origin/main; inspect/sync commits first" >&2
    exit 2
  }
fi
mkdir -p "$BASE"
export SF_ARCHIVE_DEST="$REPO/$BASE"

python3 - "$RAW" "$R26" "$R27" "$R18" <<'PY'
import hashlib, json, os, shutil, sys, zipfile
from pathlib import Path

base = Path(os.environ["SF_ARCHIVE_DEST"])
manifest = json.loads((base.parent / "SOURCE_ARCHIVE_MANIFEST.json").read_text())
for source, item in zip(sys.argv[1:], manifest["required_files"], strict=True):
    path = Path(source).expanduser().resolve()
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if path.stat().st_size != item["size_bytes"] or actual != item["sha256"]:
        raise SystemExit("BLOCKED: source size/SHA256 mismatch: " + str(path))
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None:
                raise SystemExit("BLOCKED: invalid ZIP CRC: " + str(path))
    else:
        report = json.loads(path.read_text())
        if (report.get("checked"), report.get("consistent"), report.get("status")) != (
            40, 40, "COLLATOR_INTERNAL_CONSISTENCY_ONLY"
        ):
            raise SystemExit("BLOCKED: R18 report result differs")
    dest = base / item["archive_name"]
    if dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest() != actual:
        raise SystemExit("BLOCKED: archive destination conflict: " + str(dest))
    if not dest.exists():
        shutil.copyfile(path, dest)
    print("SOURCE_SHA256_PASS", item["archive_name"])
PY

git lfs install --local >/dev/null
for file in "${FILES[@]}"; do
  [[ -f "$file" ]] || { echo "BLOCKED: expected archive item missing: $file" >&2; exit 2; }
  [[ $(git check-attr filter -- "$file") == *': lfs' ]] || {
    echo "BLOCKED: LFS filter not active: $file" >&2; exit 2;
  }
done
python3 scripts/v02_verify_before_gpu_archive.py --root "$REPO"
# Stage ONLY the four exact paths, even though *.zip is globally ignored.
git add -f -- "${FILES[@]}"
for file in "${FILES[@]}"; do
  [[ $(git show ":$file" | head -1) == 'version https://git-lfs.github.com/spec/v1' ]] || {
    echo "BLOCKED: Git index contains non-LFS data: $file" >&2; exit 2;
  }
done
echo 'LOCAL_ARCHIVE_STAGED_ONLY: four exact-hash LFS objects; unrelated changes preserved'
if [[ "$ACTION" != --push ]]; then exit 0; fi
if git diff --cached --quiet -- "${FILES[@]}"; then
  echo 'ARCHIVE_ALREADY_COMMITTED: nothing new to commit'
else
  # --only excludes unrelated staged user files, even under evaluations/by-story/.
  git commit --only -m 'archive(v0.2): preserve R18/R26/R27 and original sources before GPU training' -- "${FILES[@]}"
  mapfile -t committed < <(git diff-tree --no-commit-id --name-only -r HEAD)
  [[ ${#committed[@]} -eq ${#FILES[@]} ]] || {
    echo 'BLOCKED: resulting archive commit did not contain exactly four paths' >&2; exit 2;
  }
  for file in "${FILES[@]}"; do
    printf '%s\n' "${committed[@]}" | grep -Fxq -- "$file" || {
      echo "BLOCKED: missing archive path in new commit: $file" >&2; exit 2;
    }
  done
fi
git push origin main
echo 'PUSH_DONE: existing staged and unstaged user files were not included; verify via fresh clone'
