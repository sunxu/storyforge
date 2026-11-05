# R57 G2 source-index exporter — safe preparation receipt

**Date:** 2026-10-26 (Asia/Singapore). **Evidence tier:** verified GitHub source & synthetic CI plus previously archived source-hash receipts. No actual Owner-private eight-source JSONL replay.

## Status

`R57_G2_PINNED_SOURCE_EXPORT_TOOLING_PASS__70_SYNTHETIC_PASS__REAL_EIGHT_SOURCE_AUDIT_PENDING__NO_DATA_ADMISSION__NO_R50__NO_GPU`

This is preparation, **not G2 source-isolation PASS**. PR #5 remains a Draft until Owner signoff. R55 79/69/4 AI-assisted classification (152 category slots) and four unresolved HOLDs are not changed; R54 v0.3-A remains NO-GO; R46 remains the development comparator.

## No-GPU deliverables

- `scripts/r57_source_index_export.py`: strictly allowlisted eight historical Gold/Trainer files, file-byte SHA256 pin check, four immutable Git Blob SHA-1 checks, four previously archived compiled-Trainer SHA256 checks, explicit Owner-private alias graph, exact final target UTF-8 SHA256 and deterministic full-message/history role-content projections; output only to new private file with 0600 permissions.
- `tests/test_r57_source_index_export.py`: synthetic exported-index and fail-closed path, target, alias, byte pin, protected-path and overwrite checks. The synthetic tests do not contain private narrative or Trainer material.
- `docs/R57_G2_SOURCE_INDEX_EXPORT_OWNER_CN.md`: local-only plan/alias/source location instructions and comparison limitations.
- Existing `scripts/r57_training_lineage_audit.py` consumes an Owner-private index and emits count-only report. It does not independently open source JSONL or validate semantic world independence.

## Frozen compiled Trainer byte pins

| Data | SHA256 | Report provenance |
|---|---|---|
| R46 Train49 compiled | `a028bf9fb28b12b4a3fa352d6a60281bd9e1ef5773ebfdfecc7ac80eb2cba517` | `V02_R46_GPU_TRAINING_ACCEPTANCE_20261014.json` |
| R46 Val15 compiled | `cc8d647471423f4969149f8cabdea980aad15d8bd4424d9dd98da3313c639f3c` | same |
| R54 Train31 formal compiled | `d0425c54b534307047457d05e6890b50076ad2d23ce9ab3d52f94d1a3db585a7` | `V03_R53_FORMAL_PRIVATE_31_9_RELEASE_OWNER_RECEIPT_ACCEPTED_20261021.md` |
| R54 Val9 formal compiled | `b5ea4075419ce02a1340f6ece875068746918ce1d4c6d72ee2f799b3fe58754d` | same |

Note: R46 source-stage pins and compiled Trainer pins are not interchangeable. The R54 formal private release hashes are from the accepted Owner-side provenance workflow, not a newly independently retrieved provider copy.

## CI and limits

- R57 isolated CPU synthetic action at `b146e35380dcac1776b08e920fd35cf40dfa3c22`: 70/70 tests PASS, run [40277714885](https://github.com/sunxu/storyforge/actions/runs/40277714885).
- Whole-repo CI at same SHA: FAIL, 202 pre-existing Ruff errors, no R57-path violations in the checked log, run [40277714921](https://github.com/sunxu/storyforge/actions/runs/40277714921).
- No automatic HF CPU/GPU, training, model inference, evaluation on protected material, Dataset v0.4 sample approval or release took place.

**Remainder:** Owner must supply locally verifiable authentic compiled R46 49/15 and R54 31/9 Trainer JSONLs as well as the four Git-pinned files, exact SHA plan, and complete private story-to-alias-connected-component graph. Extraction may HOLD because historical snapshots have incompatible or absent metadata; reconstruct missing provenance separately with a traceable source join, never fabricate IDs. Run local `--mode draft`, review counts, then `--mode full` only when all eight genuine sources are present and historical 14/9/8 replay passes. Separate actual ms-swift template/collator supervision, semantic world isolation, and Owner admission remain pending.
