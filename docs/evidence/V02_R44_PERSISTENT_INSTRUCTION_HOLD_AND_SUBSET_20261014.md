# StoryForge v0.2 — R44 persistent user instruction adjudication and 71-row conservative stage

Date: 2026-10-14. **No final training authorization, no GPU launch.**

## New source-grounded decision
- Additional conservative pilot HOLD: `s14-gold-r02-t02020`, original source story rank 14, target index 2019 zero-based.
- The original player expressly prohibited future references to a specifically named grey zombie chicken at message indices 606/607. The held target later refers to the same apparently named figure by a shortened designation. This is a source-supported **persistent player-instruction fidelity** concern; it is neither a blanket content-policy finding nor a claim of independently authenticated ontology.
- Other surviving story-14 targets after the ban had no exact recurrence of the named/shortened form or the separately disallowed utterance suffix. This is a scoped review, not an exhaustive full-history canon clearance.
- Prior R42 10 quality quarantines unchanged; **R44 has 11 provisional pilot holds** among the original 82, leaving 71 candidates.

## Immutable private split, exact copy
- Train 56 unchanged: SHA256 `d94eaf861d7d86951c1ab0e60dbb38fb006998e9a6a035c19c544ba4d44862ee`.
- Validation 15 after dropping only the specified original target: SHA256 `5ebbb3c6986a5ac4d294175bab1980ee61df08536f9b8438c8a67010630f1963`.
- No Train/Validation source-story UUID overlap; known 04↔07 linked-world partition constraint retained; original 195 Gold unaffected.
- Per-row exact target SHA256 and static supervision flags PASS for 71; 71/71 samples inherited *individual* successful actual Collator records from the uploaded R43.3 remote JSON report, SHA256 `c5eef38cf8cb86892b6dcba51ae8cc8f29bc4d6df7b90c0210fc6decb226ab34`.
- The removed sample contributed 386 supervised tokens in the R43 report. Remaining Train **14,373**, Validation **4,048**, combined **18,421** supervised tokens. **No new ms-swift/HF run on R44:** this is a strict 71-item subset of the previously remotely tested 72.

## Reproducibility
- Private R44 archive: `StoryForge_v02_R44_Long_Range_Instruction_And_71_Candidate_20261014.zip` SHA256 `dcf6baeacea8297c67853503ae3230577da6bd4fe5b31eed67c00ce2faa8df70`.
- Package contains private source-anchored user directive witnesses, 56/15 exact-copy JSONLs, all 71 per-row inherited label-hash evidence, full uploaded R43 JSON, checksums and `verify_r44.py`.
- Standalone verifier returned `R44_SOURCE_BOUND_CONSERVATIVE_SUBSET_PASS 56/15; TRAINING_NOT_APPROVED`, and an intentional `gpu_authorized=true` mutation was rejected. Private narrative text stays out of ordinary Git.

## Release blockers remain
1. Comprehensive full-history narrative/canon signoff and exhaustive world/alias ontology remain **not certified**, despite source chronology and this added long-range directive check.
2. Genuinely new independent externally authored/sealed Held-out sample count **0**; historic v0.1 and assistant-authored R36 examples are not substitutes.
3. Formal Train/Validation/Test admission **0**; separate paid GPU approval **false**. No optimizer/training launched.
4. Project-owner story rights and age-legality declarations are accepted for internal use; no age/right documentation is requested.

Decision marker: `R44_PERSISTENT_INSTRUCTION_ONE_HOLD_71_STAGED_REAL_COLLATOR_INHERITED__NO_GPU_APPROVAL`.
