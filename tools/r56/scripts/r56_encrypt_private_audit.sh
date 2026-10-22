#!/usr/bin/env bash
# Only encrypts Owner-private R56 review ZIP; DOES NOT push, stage, or delete originals.
set -euo pipefail
umask 077

usage() {
  echo 'Usage: bash tools/r56/scripts/r56_encrypt_private_audit.sh --repo PATH --source PRIVATE.zip --recipient age1... --name stage5-review-20261022' >&2
  exit 2
}
repo='' source='' recipient='' label=''
while (( $# )); do
  case "$1" in
    --repo|--source|--recipient|--name)
      (( $# >= 2 )) || usage
      case "$1" in
        --repo) repo="$2" ;;
        --source) source="$2" ;;
        --recipient) recipient="$2" ;;
        --name) label="$2" ;;
      esac
      shift 2 ;;
    *) usage ;;
  esac
done
[[ -n "$repo" && -n "$source" && -n "$recipient" && -n "$label" ]] || usage
[[ "$recipient" =~ ^age1[a-z0-9]{30,}$ ]] || { echo 'BLOCK: expected explicit Owner age public recipient' >&2; exit 2; }
[[ "$label" =~ ^[a-zA-Z0-9][a-zA-Z0-9._-]{0,100}$ ]] || { echo 'BLOCK: unsafe archive name' >&2; exit 2; }
[[ "$label" != *[Rr]50* && "$source" != *[Rr]50* ]] || { echo 'BLOCK: R50 sealed materials forbidden' >&2; exit 2; }
[[ -f "$source" && "$source" == *.zip && -s "$source" ]] || { echo 'BLOCK: nonempty private zip required' >&2; exit 2; }
[[ -d "$repo/.git" || -f "$repo/.git" ]] || { echo 'BLOCK: repository root not found' >&2; exit 2; }
command -v age >/dev/null 2>&1 || { echo 'BLOCK: age not installed; brew install age' >&2; exit 2; }
# Fail closed if the plaintext archive lives under Git, even through symlinks.
python3 - "$repo" "$source" <<'PY'
import pathlib,sys
repo=pathlib.Path(sys.argv[1]).resolve(strict=True)
src=pathlib.Path(sys.argv[2]).resolve(strict=True)
if repo==src or repo in src.parents:
    raise SystemExit('BLOCK: plaintext private ZIP must remain outside Git worktree')
PY
outdir="$repo/audits/r56/encrypted"
mkdir -p "$outdir"
chmod 700 "$outdir"
out="$outdir/$label.zip.age"
[[ ! -e "$out" ]] || { echo 'BLOCK: encrypted archive already exists; no overwrite' >&2; exit 2; }
tmp=$(mktemp "$outdir/.pending-encrypted.XXXXXXXX")
trap 'rm -f "$tmp"' EXIT
age -r "$recipient" -o "$tmp" "$source"
[[ -s "$tmp" ]] || { echo 'BLOCK: encryption produced empty file' >&2; exit 2; }
[[ "$(head -c 21 "$tmp")" == 'age-encryption.org/v1' ]] || { echo 'BLOCK: unexpected age header' >&2; exit 2; }
chmod 600 "$tmp"
# We refused preexisting dest; this move still needs to fail closed on a concurrent writer.
python3 - "$tmp" "$out" <<'PY'
import os,sys
src,dst=sys.argv[1:]
try:
    os.link(src,dst,follow_symlinks=False) # atomic create, fails if destination exists
except FileExistsError:
    raise SystemExit('BLOCK: output already exists; no overwrite')
PY
rm -f "$tmp"
trap - EXIT
printf 'R56_PRIVATE_CIPHERTEXT_READY__NOT_COMMITTED\n'
printf 'CIPHERTEXT: %s\n' "$out"
shasum -a 256 "$out"
printf 'NEXT: validate decryptability with your private key OUTSIDE GIT, then git add only the .age file\n'
