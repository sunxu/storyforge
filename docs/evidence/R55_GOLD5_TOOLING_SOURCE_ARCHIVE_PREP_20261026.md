# StoryForge R55 Gold5 — source-code backup and Git archive preparation

**Date:** 2026-10-26. **Scope:** source code, synthetic tests and reviewer/Owner protocol documentation only.

## Completed backup and integrity checks
- Verified original `sunxu/storyforge` `main` contains the initial Gold5 builder, test, and owner guide. Their existing Git blob hashes match the pristine local archive.
- Recovered **30** byte-preserved source/test/doc files from previously delivered source-only bundles: **3 already present on main**, **27 missing**.
- Prepared a **29-file additive** Git patch: 27 recovered original files + `docs/R55_GOLD5_TOOLING_ARCHIVE_CN.md` + `docs/evidence/R55_GOLD5_ARCHIVED_SOURCE_MANIFEST_20261026.json`.
- Combined R55 synthetic unit tests: **176/176 PASS**. Separate rule subtype diagnostics tests: **15/15 PASS**. **Total 191/191 PASS**. Tested clean Git patch apply, file-by-file equality, and full ZIP CRC.
- Full source backup ZIP SHA256: `d9354ef7db2613869152fd2d4cb14346a4a4c1b43841f4db33d514211b064b54`.
- Standalone Git patch SHA256: `301fdc222630dcf106866e17847e848fdf77ba6786a005a821a48feaffee0d3e`.
- Thirty-source-file content manifest SHA256: `f0c788dd34084679db29b9099ef9d2613c3f5aea66fd68e3d82def9c50940bab`.
- Persistent private Library backup: `/StoryForge/R55-Tooling-Archive-20261026/StoryForge_R55_GOLD5_TOOLING_SOURCE_BACKUP_20261026.zip`. A source-only JSONL transport copy is also backed up under this Library folder.

## Git publication state and action
**Important: This document records backup preparation, NOT successful remote publication of the missing 27 source files.** The automated content-to-GitHub write was blocked; the remote `main` was confirmed unchanged at `a6ff57adbda1fe0df7438c95d77a57c90a6a4243` before this documentation commit. Do not claim missing tools are present on `main`.

On the Owner Mac, inspect the local Git tree and restore using the supplied patch, then commit only those 29 paths:

```bash
cd ~/workspace/storyforge
git status --short
shasum -a 256 ~/Downloads/StoryForge_R55_GOLD5_TOOLING_GIT_ARCHIVE_20261026.patch
git apply --check ~/Downloads/StoryForge_R55_GOLD5_TOOLING_GIT_ARCHIVE_20261026.patch
git apply --index ~/Downloads/StoryForge_R55_GOLD5_TOOLING_GIT_ARCHIVE_20261026.patch
python3 -m unittest discover -s tests -p 'test_v03_r55_gold5*.py' -q
(cd tools/r55-gold5-subtypes && python3 -m unittest discover -s . -p 'test_*.py' -q)
git diff --cached --name-only
git commit -m "audit(r55): archive reproducible Gold5 blind review and arbitration tooling"
git push origin main
```

If current worktree already has those files, `git apply --check` will fail. **Do not force or overwrite local user edits**. Reconcile the SHA256 manifest and staged paths first. A protected main requires a branch and PR instead of direct push.

## Exclusions and evidence boundaries
No private story original, anonymized candidate/response, reviewer scorecard, identity mapping, completed verdicts, HF credential, model checkpoint, or protected R50 file is in this source archive. The old R55 diagnostic set was already exposed: 152 decisions have format/quote validation, but **not** independent semantic certification, and 4 HOLD remain. R54 v0.3-A remains NO-GO; no inference, training or promotion by this backup task.

**Status:** `R55_GOLD5_SOURCE_BACKUP_PERSISTED__191_SYNTHETIC_PASS__GIT_PATCH_VERIFIED__REMOTE_TOOL_SOURCE_PUSH_PENDING`.
