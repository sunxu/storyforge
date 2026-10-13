# StoryForge v0.2 — full evidence, stories 06–15

The original full evidence backup **StoryForge_v02_06-15_Full_Evidence_20261013.zip** (65,332,700 bytes) was built, verified locally and uploaded via Git LFS in commit `e3508ed`. **Remote status: `REMOTE_VERIFIED`** based on the repository owner's reported `REMOTE_LFS_PASS` from a fresh clone with `git lfs pull`, file-size verification, matching SHA256 and ZIP CRC verification. The assistant independently verified the Git commit and LFS pointer, but **did not independently retrieve the complete LFS binary**.

## Already archived in this Git directory

The `snapshots/` directory contains byte-exact original frozen candidate records from R01 (63), R02 (90), R03 (120) and R04 (150), with SHA256 in `source_bundle_manifest.json`. R01→R02→R03→R04 prefixes are byte-identical. The independent double-ACCEPT 108 are preserved unchanged in `../../gold-quality-108/` with reviewer scores and selection index. Use `verify_snapshots.py` to check the Git-resident snapshots.

## Original full ZIP (Git LFS — fresh-clone verified)

The original backup includes 10 raw story ZIPs (each with source JSON and JSONL), ten R01 curation packages, original R02/R03/R04 deliveries, A/B preflight prompts and generator plans, original Reviewer 1 and Reviewer 2 150-row assessments, the 150-row dual review reconciliation and later administrator arbitration. It includes exact frozen 150 and double-ACCEPT 108 extracts, evidence manifest, read-only full-source validator and SHA256SUMS.

After downloading the ZIP, validate it against `source_bundle_manifest.json`. Extract it and run `python3 verify_bundle.py`; this checks SHA256, nested ZIP CRC, all 150 source target and history records against originals, frozen prefix and original R04 verifier, and verifies that the 108 records are exactly those with two ACCEPT decisions. The separate six arbitration-only approvals remain excluded.

The Git LFS object is recorded by the pointer SHA256 `b874cd07547092e9c3c967f69fab6b75262ff4f44ba2d368fd575f84e8886afb`. On 2026-10-13 the repository owner reported `REMOTE_LFS_PASS` after the prescribed fresh-clone download and integrity checks. The validation evidence and attestation level are recorded in `source_bundle_manifest.json` and `remote_lfs_verification_20261013.json`. Re-run the independent retrieval checks whenever moving the archive to another storage system.

**Training admission:** `PENDING_NOT_APPROVED`. First cohort 87 unchanged. Required future gates: full canon and role cards, ages/content, 04↔07 isolation, story-level heldout split check, Qwen 16,384-token check, and actual final Assistant-only loss mask. No new GPU or Hugging Face job.

**Privacy:** preserve private-repository visibility; full source archives contain original conversations.
