#!/usr/bin/env bash
# Run inside your trusted clone of sunxu/storyforge; Git LFS is required.
set -euo pipefail
EXPECTED_SHA='b874cd07547092e9c3c967f69fab6b75262ff4f44ba2d368fd575f84e8886afb'
EXPECTED_BYTES=65332700
NAME='StoryForge_v02_06-15_Full_Evidence_20261013.zip'
SRC="$1"
[[ -f "$SRC" ]] || { echo 'Missing backup ZIP'; exit 2; }
[[ "$(basename "$SRC")" == "$NAME" ]] || { echo 'Unexpected ZIP filename'; exit 2; }
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
case "$(git remote get-url origin)" in
  *github.com[:/]sunxu/storyforge|*github.com[:/]sunxu/storyforge.git) ;;
  *) echo 'Unexpected origin; expected sunxu/storyforge'; exit 2;;
esac
[[ "$(git branch --show-current)" == main ]] || { echo 'Checkout main first'; exit 2; }
git lfs version >/dev/null || { echo 'Install Git LFS: brew install git-lfs'; exit 2; }
[[ -z "$(git diff --cached --name-only)" ]] || { echo 'Unrelated staged changes; stop'; exit 2; }
[[ "$(wc -c < "$SRC" | tr -d ' ')" == "$EXPECTED_BYTES" ]] || { echo 'ZIP size mismatch'; exit 2; }
[[ "$(shasum -a 256 "$SRC" | awk '{print $1}')" == "$EXPECTED_SHA" ]] || { echo 'ZIP sha256 mismatch'; exit 2; }
unzip -tq "$SRC" >/dev/null
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || { echo 'Sync main first'; exit 2; }
DIR='evaluations/v0.2/source-archives/06-15'
DEST="$DIR/$NAME"
mkdir -p "$DIR"
if [[ -e "$DEST" ]]; then
  [[ "$(shasum -a 256 "$DEST" | awk '{print $1}')" == "$EXPECTED_SHA" ]] || { echo 'Destination has different content'; exit 2; }
else
  cp "$SRC" "$DEST"
fi
git lfs install
git lfs track "$DIR/*.zip"
[[ "$(git check-attr filter -- "$DEST")" == "$DEST: filter: lfs" ]] || { echo 'LFS not active'; exit 2; }
git add .gitattributes "$DEST"
git commit -m 'archive(v0.2): upload full original 06-15 evidence to Git LFS'
git push origin main
git lfs push origin main
git lfs fetch origin main
git lfs checkout "$DEST"
[[ "$(wc -c < "$DEST" | tr -d ' ')" == "$EXPECTED_BYTES" ]] || { echo 'LFS object size mismatch'; exit 2; }
[[ "$(shasum -a 256 "$DEST" | awk '{print $1}')" == "$EXPECTED_SHA" ]] || { echo 'LFS object SHA mismatch'; exit 2; }
echo 'Local object PASS. Verify from a fresh clone before marking remote LFS VERIFIED.'
