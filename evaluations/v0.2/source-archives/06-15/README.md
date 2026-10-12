# StoryForge v0.2 — full evidence, stories 06–15

The original full evidence backup **StoryForge_v02_06-15_Full_Evidence_20261013.zip** was constructed and verified locally (65,332,700 bytes). Its complete **binary bytes have NOT yet been uploaded to GitHub LFS**. The manifest is not a substitute for the binary archive. Do not treat a future LFS pointer alone as a successful upload.

## Already archived in this Git directory

The `snapshots/` directory contains byte-exact original frozen candidate records from R01 (63), R02 (90), R03 (120) and R04 (150), with SHA256 in `source_bundle_manifest.json`. R01→R02→R03→R04 prefixes are byte-identical. The independent double-ACCEPT 108 are preserved unchanged in `../../gold-quality-108/` with reviewer scores and selection index. Use `verify_snapshots.py` to check the Git-resident snapshots.

## Original full ZIP (prepared offline, LFS upload pending)

The original backup includes 10 raw story ZIPs (each with source JSON and JSONL), ten R01 curation packages, original R02/R03/R04 deliveries, A/B preflight prompts and generator plans, original Reviewer 1 and Reviewer 2 150-row assessments, the 150-row dual review reconciliation and later administrator arbitration. It includes exact frozen 150 and double-ACCEPT 108 extracts, evidence manifest, read-only full-source validator and SHA256SUMS.

After downloading the ZIP, validate it against `source_bundle_manifest.json`. Extract it and run `python3 verify_bundle.py`; this checks SHA256, nested ZIP CRC, all 150 source target and history records against originals, frozen prefix and original R04 verifier, and verifies that the 108 records are exactly those with two ACCEPT decisions. The separate six arbitration-only approvals remain excluded.

Run `upload_full_bundle_lfs.sh /absolute/path/StoryForge_v02_06-15_Full_Evidence_20261013.zip` from a trusted local checkout to finish the binary Git LFS upload; then re-download from a fresh clone and compare the exact hash. Only then may the remote-LFS status be marked verified.

**Training admission:** `PENDING_NOT_APPROVED`. First cohort 87 unchanged. Required future gates: full canon and role cards, ages/content, 04↔07 isolation, story-level heldout split check, Qwen 16,384-token check, and actual final Assistant-only loss mask. No new GPU or Hugging Face job.

**Privacy:** preserve private-repository visibility; full source archives contain original conversations.
