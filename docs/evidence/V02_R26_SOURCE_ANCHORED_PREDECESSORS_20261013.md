# StoryForge v0.2 — R26 source-anchored preceding-context audit

**Date:** 2026-10-13. **Admission:** `PENDING_NOT_APPROVED`. No training and no changes to the 195 frozen Gold source replies.

## Verified from the private original uploaded JSONL archive

- Parent R25 archive SHA256: `af521e0052028142549f6dbd220ca21bee3bfa1c32b6dfbb2c32eb7b1f171fdb`.
- Original user-uploaded source ZIP SHA256: `050af7034f9b2f3ef0401542364d23ef6ce126dd1699a49b1124d69245c98fdb`. Confidential source ZIP is not committed or redistributed.
- **195/195** current synthetic visible histories (role plus exact text) match contiguous source messages preceding their frozen target response in the supplied JSONL snapshot. **195/195** original target IDs/bodies/timestamps retain the R25 evidence. The R07 synthetic System prompt is NOT authenticated as the original model request.
- For **132/132** windows whose first Assistant history message had been removed, the immediately preceding original **User–Assistant** pair was located with exact IDs, UTF-8 body SHA256s, source turn indices, statuses and timestamps. The preceding pair and the existing preview start form contiguous source turns. Exact private texts are retained *only* in the R26 ZIP as non-training witness records. **No revised model-ready training prompt was created.**
- **130/132** recovered spans have no nonzero `mutation_revision` flags in either the recovered pair or remaining preview history. The other **2** have historical message revision flags. The same two candidates also have nonzero target revision flags: `s09-gold-r04-t03104` (target revision 4) and `sf14-gold-t02392` (target revision 3). Original at-creation target/context text is not established without revision logs.
- An independent temporal integrity check found **296** adjacent `created_at` inversions within **69** candidate context spans. The largest is **55.65 ms**. Source `turn_index` remains contiguous, but timestamps must not be assumed strictly monotonic or treated as exact model-request start order.
- Of **195** candidates, **89** belong to a story with indexed historical card snapshots. Of those, **59** have a snapshot source-update time not after target time and **23** have a snapshot archive time not after target time. These are merely chronological evidence candidates. **Zero** target-request-effective card versions, ages or full original request prompts have been proved.

## Operational boundaries

Recovered source messages can support a newly reviewed context; they do **not** prove which hidden system instructions, exact card version, memory snapshot or template the original model saw. Do not count 132 source-based restorations as lossless historical request reconstructions or training admission PASS. Prior 38 HOLD, special content/age gates, connected-world isolation, fresh unseen held-out population and final Train/Validation/Test split all remain blocking.

R18's previously reported 40/40 tokenizer and `last_round` label internal consistency applies to the older preview, not a new derived dataset. Final-context re-tokenization and actual label-mask audit remain required after any eventual approved rewrite of derived inputs.

## Audit package

- Private artifact `StoryForge_v02_R26_Source_Anchored_History_20261013.zip`: SHA256 `4ad742260826ff02b643232a9bdef56d669c5b4bea07215ddc47c8d2047538c9`; **1,811,375 bytes**.
- It includes the immutable R25 ZIP, source-hash/turn anchor tables for 195 and 132, two mutation cases, the 296 timestamp-anomaly ledger, R22 card temporal observations, the unchanged R15 route ledger, a strict original-ZIP replay tool, SHA256SUMS and an offline integrity verifier.
- Source replay against the private original ZIP reproduced the recovery witness JSONL and timestamp anomaly CSV byte-for-byte. Independent unzip and `verify_r26.py` PASS. Deliberate witness tampering was rejected (nonzero exit). The portable verifier only checks exported witnesses and gate integrity, not the original bytes unless replayed with the private ZIP.
- Original source and private witness text are **not** committed in this GitHub documentation. Formal training status is `PENDING_NOT_APPROVED`.

**Next R27:** request-time prompt and effective card revision logs, revision history for both mutated targets, assessment of millisecond timestamp semantics, human review of proposed source-based context updates, final linked-world split, unseen held-out selection and full final-input token/mask audit.
