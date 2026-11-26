# R50 W17 — Private seven-gap AI workpaper file preflight

**Reported error:** `R50_W17_SEVEN_GAP_WORKPAPER_HOLD:
ValueError PRIVATE_WORKPAPER_NOT_SAFE`.

This error occurs **before** any of the seven private gap decisions are read.
The old validator combined all file-path/permission cases into one marker,
so it is not possible to infer which one happened from the terminal output.

This update differentiates (no private path or story material printed):

- `PRIVATE_WORKPAPER_FILE_MISSING`: reviewer did not create the
  expected JSON at that location, or the path argument is wrong
- `PRIVATE_WORKPAPER_SYMLINK_FORBIDDEN`: final path is a symlink;
  inspect manually, do not follow or silently overwrite
- `PRIVATE_WORKPAPER_NOT_REGULAR_FILE`: it is a directory/special file
- `PRIVATE_WORKPAPER_INSIDE_GIT_FORBIDDEN`: path resolves into a Git checkout
- `PRIVATE_WORKPAPER_PERMISSIONS_NOT_0600`: other users/groups have file
  access (for example mode 0644)
- `LOCAL_GIT_CHECKOUT_REQUIRED`: incorrect `--repo` path

It also blocks parent-directory symlink tricks that would resolve the workpaper
inside the repo. It does not auto-chmod, overwrite, rename, re-run AI, or
alter the seven review judgements. The pinned manifest remains SHA256
`b4e08232bdd12d9401d78fe6e0ab945a6f5156938c88ef811da9bf52a9b41a3b`.

## On the Mac: inspect file metadata ONLY

```bash
cd ~/workspace/storyforge
git fetch origin audit/r49-r50-source-intake-20261015
git switch audit/r49-r50-source-intake-20261015
git pull --ff-only

ROOT="$HOME/.local/share/storyforge/r50/private-ai-review"
WORKPAPER="$ROOT/W17_SEVEN_GAP_AI_WORKPAPER_PRIVATE_20261019.json"

if [ -L "$WORKPAPER" ]; then
  echo "WORKPAPER_IS_SYMLINK__REVIEW_MANUALLY"
elif [ ! -e "$WORKPAPER" ]; then
  echo "WORKPAPER_MISSING__REVIEWER_OUTPUT_NOT_FOUND"
elif [ ! -f "$WORKPAPER" ]; then
  echo "WORKPAPER_NOT_REGULAR_FILE"
else
  stat -f 'WORKPAPER_MODE=%Sp  BYTES=%z' "$WORKPAPER"
fi

python3 scripts/v03_r50_verify_seven_gap_workpaper.py \
  --repo . \
  --packets-dir "$ROOT/W17_SEVEN_GAP_CONTEXT_PACKETS_20261019" \
  --workpaper "$WORKPAPER"
```

Do not print or paste the JSON itself. If the file is present, regular,
outside Git and not a symlink, but too permissive, **only then** do
`chmod 600 "$WORKPAPER"` and rerun the validator. This changes
permissions **not** the content hash. If absent, do not fabricate or
autogenerate a workpaper. Inspect the separate AI review run's local
completion/error logs, its `--output-last-message` destination, and
whether it was actually authorized to read all seven packets.

Successful preflight is not evidence of a successful independent semantic
review. The validator will continue to verify the exact pinned seven
packets and the AI's private source references. All previous results,
46 original candidate tests, `SEMANTIC_HOLD` and `NO_FINAL_SEAL`
remain unchanged.
