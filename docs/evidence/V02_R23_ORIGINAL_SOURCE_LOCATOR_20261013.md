# StoryForge v0.2 — R23 original-source provenance and checkpoint preflight

**Review date:** 2026-10-13. **Training admission:** `PENDING_NOT_APPROVED`. **Original 195 Gold replies:** unchanged. **No training Job started.**

## Evidence found

- Original supplementary `source_chat_export.path` and `source_chat_export.sha256` were recovered for **13/13** v0.2 story UUIDs from the provided supplementary evidence ZIP. The original source-chat JSON files were **not contained in the source-card/checkpoint supplement**, and **0/13 source export bytes have been verified** in this environment. Do not confuse a file-reference digest with a verified original source.
- For the R18 first-lane **40** candidates, target UUID, story UUID, source turn index and target-response SHA256 align with the immutable R07 preview. This proves response provenance inside the frozen curation archive, **not** the source message `created_at`.
- The supplement contains **13 relationship checkpoint streams** with their own `turn_index` and `created_at`; their nearest positions relative to the 40 target indices are **9 same-turn, 13 between checkpoints, 17 after last checkpoint, 1 before first checkpoint**. These timestamps describe *state snapshots*, not the target generation request or assistant-message timestamps. Therefore **0/40 exact target-created-at joins** and **0/40 as-of card-version approvals**.
- Historical R22 corrected inventory of **38** archived story-card revisions is unchanged, with no proven effective `[valid_from, valid_until)` mapping to any target message.
- The previously verified v0.1 Train exact UUID overlap (21 v0.2 candidates) remains quarantined. The R18 40 have no exact historical story UUID overlap; shared IP, characters, aliases and story-world components are still not proved disjoint.
- **0** approved v0.2 Train/Validation/Test assignments, **0** new genuinely unseen held-out stories, **0** full-history content/age signoffs.

## Additional artifact and executable check

Private R23 audit package SHA256: `9fdc43839ae2ab03a7648eaaac4bfe35d35d7a2a1962d1c972281517f064de76` (189820 bytes). The package contains the unchanged R22 ZIP, 13 export locators, 13 checkpoint SHA records, 40 per-target nearest-checkpoint references, 40 immutable target-ID/content-hash join requests, and a **fail-closed** Python program `r23_verify_original_source_join.py`. The checker is intended to run on the **owner's original private source exports**, not on R23 cards. An empty source directory returns `BLOCKED` (exit 2), and does not fabricate event timestamps. It writes no source text. No raw dialogue, full source file or character-card text is placed in this GitHub report.

The independent unpack-and-verify result is `R23_PROVENANCE_LOCATOR_AND_CHECKPOINT_INTEGRITY_PASS_ONLY`. This validates the produced manifest, immutable R22 parent hash, row identities, and all reported non-approval gates. It **cannot validate any absent source-chat bytes, target-message time, model-request card version, licensing or safety approval**.

## Next action: R24 source acquisition

Locate the owner-side `by-story/*.json` exports by the **exact basename and SHA256** in the private R23 manifest. Then run:

```bash
python3 r23_verify_original_source_join.py \
  --source-dir /private/path/to/by-story \
  --output-dir /private/path/to/r23-results
```

A successful source-join-only result must **not** be interpreted as story-card/age or training admission approval. Separately retrieve actual request-effective card IDs and immutable card revisions, linked-world/alias evidence, human content/age signoff and genuinely new pre-registered held-out groups. Do not assign splits or launch training before these checks.
