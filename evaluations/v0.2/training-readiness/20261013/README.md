# StoryForge v0.2 pre-GPU source archive — 2026-10-13

**Training admission: `PENDING_NOT_APPROVED`. This is an archive, not a release.**

This folder stores a byte-exact SHA256 manifest, and its `private/` subdirectory is reserved for **four Git LFS objects** containing the minimum reproducible source data and engineering evidence for the provisional R27 corpus. **The four blobs have not been uploaded to GitHub by creating this manifest.** Git pointer files alone are insufficient for recovery.

| Required file in private/ | Bytes | Purpose |
|---|---:|---|
| `original_chat_jsonl_14_20261013.zip` | 57,602,487 | 14 original chat exports, independently supplied by the project owner |
| `R26_Source_Anchored_History_20261013.zip` | 1,811,375 | Anchored original-history witnesses and R25 ancestry |
| `R27_HF117_Fix_20261013.zip` | 405,814 | Exact 117 provisional inputs, 195 route ledger, 96/21 proposed groups, builder, verifier and corrected CPU worker |
| `R18_HF40_Actual_Collator_Report_20261013.json` | 19,308 | Remote Qwen/ms-swift no-training 40/40 collator report |

All four original expected SHA256 values are in [SOURCE_ARCHIVE_MANIFEST.json](SOURCE_ARCHIVE_MANIFEST.json). The R27 internal candidate file must remain `r27_private_candidate_117_NOT_APPROVED.jsonl` with SHA256 `cdecc311f05e2c700f1038f3afca09c889ff681d4ef55dc18dc7426c9d14a92a`. **Do not rewrite or promote its content in place.**

## Owner-side archive upload

The private ZIPs are downloaded from the prior ChatGPT conversation; `r18_actual_no_train_report.json` is the real HF report the owner previously downloaded. From a clean **private** checkout:

```bash
git pull --ff-only origin main
brew install git-lfs   # skip when already installed
git lfs install
bash scripts/v02_archive_before_gpu.sh \
  "$HOME/Downloads/归档(1).zip" \
  "$HOME/Downloads/StoryForge_v02_R26_Source_Anchored_History_20261013.zip" \
  "$HOME/Downloads/StoryForge_v02_R27_HF117_Fix_20261013.zip" \
  "$PWD/r18_actual_no_train_report.json" --push
```

The command first checks all four sizes, SHA256, ZIP CRC and the actual R18 report. It requires the correct origin, main branch and Git LFS filter. `--push` commits and pushes only these four files. Omit `--push` to stage and inspect without uploading. **No CPU or GPU Job is run.**

**Unrelated local files are safe:** the upload script permits existing modified or staged `evaluations/by-story/*.jsonl` and other work. It commits with `git commit --only --` and four explicit source-archive paths, preserving unrelated staged/unstaged edits. It first verifies that `main` has no unpushed older commits compared with `origin/main`. If your checkout has not been updated since this fix, run `git pull --ff-only origin main` before retrying; **do not reset, delete, or stash the original by-story files merely to satisfy the archive script.**

To confirm that the **remote binaries** exist (not merely LFS pointer files), perform a fresh clone:

```bash
cd "$(mktemp -d)"
git clone git@github.com:sunxu/storyforge.git
cd storyforge
git lfs pull
python3 scripts/v02_verify_before_gpu_archive.py
```

Only after that test passes may the operator record `REMOTE_LFS_PASS`. Do not add a false status to the immutable manifest. You may instead compare `git lfs ls-files -l` and report object OIDs, but fresh-clone full-file hashes are stronger evidence.

## Remaining pre-training blockers

R27 contains **117 unapproved provisional candidates** (77 source-restored, 40 existing visible windows). R18's 40/40 actual Token/Mask pass is not a substitute for a **successful** final-input HF audit of all 117; the previous R27 Job `6ace178cc66288145222a476` failed with a stale `118` file path. Full content/age clearance, request-effective card or authorized synthetic-card policy, connected-world isolation, an untouched held-out set, approved Train/Validation/Test assignment and formal approval remain open. **Do not launch formal GPU training.**

**Privacy:** the raw conversation archive contains chat text and potentially sensitive narrative context. Keep the repository private and restrict collaborators. Git LFS objects are accessible to people with access to this GitHub repo. Do not commit API tokens, credentials or model weights. Avoid accidentally publishing these archives through GitHub Actions logs or public releases.
