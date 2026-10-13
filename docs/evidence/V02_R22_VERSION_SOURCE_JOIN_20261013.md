# StoryForge v0.2 — R22 source version-schema correction (2026-10-13)

**Formal training admission: `PENDING_NOT_APPROVED`.** No training was launched and the original 87 + 108 Gold text was not changed.

## Evidence correction

The R21 as-of preflight read an absent field called `story_content_versions`, reporting 0 archived versions across 13 supplementary card documents. The *actual source schema* uses `content_versions`. R22 re-read the byte-verified supplementary ZIP, obtaining **38 archived card-version records across 6 of 13 story cards**, each indexed by SHA256 and source updated / archive timestamps. This corrects the *inventory count*, not the approved as-of version count.

Per-story counts within the private audit are 25, 6, 3, 2, 1 and 1 (38 total). Six of the thirteen source card exports lack archived versions. Version records are observational and may not reconstruct which exact version was supplied to any historical generation request.

## Source mappings and character identity

The 40 R18 diagnostic candidates were joined to immutable source `target_message_id` and original physical turn index using frozen 87- and 150-candidate metadata. The R07 synthetic preview contains **no target event timestamp** and frozen selected metadata does not establish a validated target-time-to-effective-card join. Therefore **0/40** candidates have verified target-time card/age evidence; no post-hoc cards were injected into prompts.

Thirty *export-time* character records were examined from the thirteen supplementary story cards. **Zero exact character-ID cross-story collisions** and **zero exact normalized-name cross-story review signals** were observed in this specific source scope; these checks do not establish canonical connected-world or IP independence. The previously proven v0.1 Train exact story UUID collision involving 21 v0.2 frozen candidates remains in quarantine.

## Blocking inputs to obtain

Original target-message timestamps, the actual effective story-card version used at the request time, linked-world/alias evidence across v0.1 and v0.2, complete age and content signoff, and a new untouched held-out story/component population are still missing. **Zero v0.2 Train/Validation/Test assignments and zero newly reserved held-out cases.** Re-rendering and re-auditing any final-context training derivative also remains unperformed.

The complete R22 ZIP retains the R21 baseline and records: 13 card summaries, 38 archived version SHA256 entries, 30 export-only identity rows, 40 missing join requests, 195 unchanged admission routes, and a read-only verifier. No original dialogue or card text is committed here.

- R21 parent SHA256: `a9cccce1d9324b248efebaa70e1b1758059e6c22a949de3f12d66a16df174d9a` (as asserted by R21 from R20 is **not** the R21 ZIP; see R22 private report for the exact parent hash).
- R22 private ZIP SHA256: `01e5f89b975f5cdda64f67a3d95534ca1218c36217c27e8018390b29f5cddca5`
- Portable verifier: `R22_INVENTORY_AND_ROUTING_INTEGRITY_PASS_ONLY`. It does not prove request-time canon or policy approval.

**Disposition: `PENDING_NOT_APPROVED`.**
