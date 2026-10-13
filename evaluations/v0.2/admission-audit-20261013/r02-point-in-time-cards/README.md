# StoryForge v0.2｜训练准入审计 R02 — 目标时刻故事卡

**2026-10-13 / READ-ONLY / BLOCKED_NO_VERIFIED_TARGET_TIME_CARDS**

This is an additive review of the **108 original-text double-ACCEPT candidates** from stories 06–15. It does not change the prior 87 or second 108, does not create splits, does not infer new character facts, and does not approve SFT.

## Confirmed directly from the original raw archive

- All 108 source target Assistant messages match their original messages. The complete evidence ZIP SHA256 is `b874cd07547092e9c3c967f69fab6b75262ff4f44ba2d368fd575f84e8886afb`.
- Original JSON and JSONL exports agree for each of the 10 stories. They are **two representations of the same export**, not two historical versions.
- All **10/10 source export metadata** explicitly states that story/persona/runtime context is an **export-time snapshot, not the historical system prompt of each turn**.
- In **44/108** cases the export-time story-card `updated_at` postdates the target Assistant message (story 08: 4, 10: 19, 13: 16, 15: 5). The remaining 64 have no such order inversion but **still lack independently verified as-of card versions**.
- All 10 `current_persona` export snapshots are null; 13 selected target messages contain event-runtime metadata, but **event state is not the full story card / original system prompt**.
- Three selected records use a verified `source_story_id` fallback without editing frozen records.
- Export-time partial character age fields cannot verify player ages or age/consent/content constraints at the historical turn.

## Machine-readable evidence

- `candidate_card_version_evidence_108.csv`: 108 source timestamp/hash/status records, no story text
- `source_story_inventory_10.csv`: source ZIP identity, export semantics, story-card digest, age-field structure
- `card_provenance_r02.json`: status and counts
- `point_in_time_card_evidence_contract.md`: requirements for genuine original request/system prompt or immutable as-of card versions

The complete local [R02 audit ZIP] is also available in the conversation. It includes the standard-library `audit_r02.py` that rechecks the 65,332,700-byte source ZIP, all ZIP CRCs, 10 original JSON/JSONL pairs, and 108 candidate-to-target correspondences. Its CSV Git blobs here were checked against the exact locally generated Git blob SHAs.

No complete verified target-time system prompt has been recovered for any of the 108; therefore tokenizer accounting and real ms-swift last-round loss-mask audits **cannot yet be marked PASS**. A strategy that excludes unverified cards would be a new supervised task specification requiring separate review, not a silent fix.

**Training remains `PENDING_NOT_APPROVED`.** No training, no HF/GPU actions, no modification of quality data.
