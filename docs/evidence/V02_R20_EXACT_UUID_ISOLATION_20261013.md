# StoryForge v0.2 R20 — Exact UUID isolation and content-review preparation (2026-10-13)

**Training admission:** `PENDING_NOT_APPROVED`; **training executed:** NO. Original 87+108 Gold responses remain frozen.

## New verified source evidence

Using the authenticated GitHub repository `sunxu/storyforge`, the original frozen v0.1 Dataset v0.3 split blobs were read and their `metadata.story_id` fields enumerated: **Train 65 samples/15 stories; Validation 15/2; Test 20/2**. Git blob identities:

- Train `3e64c9932ca43fefa8ecfb200085fe718581b6f9` (original SHA256 `9a24f07befee9e701c587f4b154b0e780c29534abe3a0fa8b0c310511172a60f`)
- Validation `db0ae8b86038be1b372d547fdb2d6b0b7e33b54e` (original SHA256 `083a6f124abc414a0edf268d1a95788f738d55e7ecd229a78c67087991f46c36`)
- Test `c17f225967b6b2f8cbaf3d82fadac1b4031d0654` (original SHA256 `d8eee6db5882d85dce7ffc01256e7c5b9b46e133bdb2cf8591259112b92e980d`)

**Confirmed exact UUID overlap:** `dc87aac6-cf4f-4422-a12b-534fea3a487d`, 《京圈的灯火与暗流》, occurs in v0.1 Train (**2 historical samples**) and the v0.2 quality-frozen corpus (**21 candidates**). All these v0.2 candidates were already in the existing R15 HOLD/truncation quarantine. It must not be described as a genuinely fresh independent v0.2 story.

The **40 R18 diagnostic samples / 10 story UUIDs have zero exact UUID collisions** with the recovered 19-story v0.1 registry. This proves only literal story-ID disjointness; aliases, linked worlds, shared characters and text near-duplicates remain unverified.

## Content review & engineering scope

R20 establishes a per-candidate user/target excerpt evidence ledger for all 40 cases (stored only in the private chat audit ZIP), with review foci such as school-setting age facts, clinical relationships, intimate-context consent, family/child context and player autonomy. These foci **are not policy violations or final safety clearance claims**; every case still awaits context-effective canon and human policy signoff.

R18 remote actual `last_round` loss mask diagnostic remains **40/40 reported pass** (HF Job `6acdeae181fefd5110e1963c`), and **25/40** original diagnostic records lack `split_group`. A real post-canonical connected-component partition, independently fresh held-out data and a new end-to-end data pipeline audit are still required. **Zero v0.2 samples were assigned Train/Validation/Test.**

## Artifacts and verification bounds

- R19 parent ZIP SHA256: `788a0cacf04045ff34b9263bf34c0ac9d17c56ee39532bd84b3ac3ab9e3f8789`
- R20 private ZIP SHA256: `a9cccce1d9324b248efebaa70e1b1758059e6c22a949de3f12d66a16df174d9a`
- R20 portable verifier result: `R20_EVIDENCE_AND_UUID_MEMBERSHIP_PASS_ONLY`; checks 19/13 story memberships, 195 freeze-route IDs, 40 excerpt digests, R19 parent hash and non-approval controls. It does **not** independently re-fetch remote v0.1 split bytes or re-execute model labels.
- Private R20 ZIP includes the R19 historical parent, complete UUID membership registry, 195-route isolation table, 40 excerpt evidence anchors, and verifier. **No original story text is committed to GitHub here.**

All content approvals, effective-date story-card facts, cross-world edge proofs, new unexposed held-out test selection and final train split remain **BLOCKED/PENDING**. **No formal training approval.**
