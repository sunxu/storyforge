# StoryForge R56 — Owner CPU replay receipt received (2026-10-22)

**Scope:** count-only receipt registration, not independently verified source-output replay and not Held-out admission.

- Receipt schema: `storyforge-r56-owner-local-CPU-actual-repo-receipt-v1`.
- Owner-reported result: `LOCAL_R56_REAL_GOLD195_PRESCREEN_PASS__ALL24_HOLD`.
- Git commit identified by Owner's receipt: `abaea6d65cabcc546c552ff612f0e7a463306b44` (exists as a GitHub commit).
- Original synthetic R56 unit-test count reported: 11. Individual owner log not attached to this conversation.
- Original source summary: Gold195 / 13 story UUIDs / 11 historically overlapped worlds (163 rows) / 2 no-known-UUID-overlap worlds (32 rows).
- Provisional pool: story03 12 + story05 12 = 24 **HOLD**. Extra independent worlds needed: 2.
- Official test admitted: **0**. Independent semantic world and case review: **HOLD**.
- R50 access / GPU job / training / model promotion: **false as reported in receipt**.
- Owner receipt contains SHA256 of original prescreen summary and deep count-only JSON. Neither underlying file was attached here, so **their bytes were not independently rehashed**.
- A separate CPU-only verification kit has 9/9 new synthetic unit tests passing and can cross-check both SHA256 hashes, actual 195/163/32/24/0 counts, 11+7 Mac test logs, HOLD-only CSVs, and five frozen Git source blobs.

**State:** `RECEIPT_STRUCTURALLY_VALID__REFERENCED_EVIDENCE_NOT_YET_RECHECKED`.

Next steps: verify the actual owner output directory using the local checker; then independently review the 32 private candidates and cross-world relations, and discover two genuinely new worlds. If four worlds become qualified, freeze 6 cases per world, not the original 12+12. Two-world results may only be exploratory development evaluations; never represent them as four-world Fresh Held-out. No model promotion or new paid GPU authorization is implied. Gold unchanged.

## Frozen-template SHA256 reproduction (additional independent consistency check)

Reconstructed the exact two expected count-only JSON strings using the frozen R56 source code's field ordering, values and JSON formatting, without reading the Owner's Mac output files. Both SHA256 digests exactly match the two hashes inside the Owner receipt. This is stronger than receipt field validation, but **does not** verify that the actual Mac output files match or that every historical and content gate passed. A full Owner-output byte-and-log check remains pending.

The local verifier's synthetic regression suite now passes 10/10 tests. The counts-only verifier report marks both template-hash matches true, actual output-file verification false, and formal test admission 0.
