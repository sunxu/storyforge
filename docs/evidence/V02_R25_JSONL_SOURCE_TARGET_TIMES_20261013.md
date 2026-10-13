# StoryForge v0.2 — R25 uploaded JSONL source-target provenance (2026-10-13)

**Admission:** `PENDING_NOT_APPROVED`. **Training:** not started. **Frozen Gold:** unchanged (87 + 108 = 195).

## Material examined
- User-supplied private ZIP `归档(1).zip`, SHA256 `050af7034f9b2f3ef0401542364d23ef6ce126dd1699a49b1124d69245c98fdb`. This private archive is **not committed to Git**.
- Fourteen `.jsonl` entries, each consisting of a JSON object with a `messages` array. Thirteen required story and session UUIDs from the R23 manifest matched; one additional `處女之死` session was excluded from required provenance.
- 62,583 message records in all 14 sources; 58,783 records in the 13 required sessions.

## Real results
- Replayed R07 immutable **195** candidate target UUIDs and UTF-8 target-body SHA256s against the uploaded JSONL.
- **195/195** unique target message UUID, story/session ID, completed Assistant role, exact body SHA256 **in supplied snapshot**, and timezone-aware `created_at` joins PASS.
- All **40/40** earlier R23 first-lane join requests are an exact subset with identical target timestamps.
- Target creation timestamp interval: 2026-07-07 through 2026-10-08 UTC. No private per-message timestamp table is committed here.
- **132** candidates were marked with R07 leading-Assistant truncation and now have target-message timestamps; **0** windows were thereby proven semantically lossless or training safe.
- **193/195** target messages have `mutation_revision=0`; **2/195** have nonzero revisions: `s09-gold-r04-t03104` has revision 4 and `sf14-gold-t02392` has revision 3. Their **current** content hashes agree with frozen targets, but historical content at original message creation time is **not proven** without mutation/revision history.

## Limits that must not be silently lifted
- R23 expected original **.json** files and their SHA256. These are supplied **.jsonl** exports, with different bytes. **0/13 byte-exact original JSON checks passed**; the PASS is a per-target source-message identity/body/time join only.
- `created_at` is a message timestamp, **not** the model request's effective card version ID or a proof of the exact prompt, historical character ages, or user consent at generation.
- 40 first-lane message metadata records lack explicit card-version IDs. **0** request-effective card-version joins approved.
- Historical R18 **40/40 reported** tokenizer and collator test remains unchanged; derived final-context train inputs were not rerendered or audited.
- All unresolved content/age, 38 HOLD, 132 opening-truncation, shared-world, fresh held-out and Train/Validation/Test split gates remain pending.

## Evidence custody and reproducibility
Private ChatGPT artifact: `StoryForge_v02_R25_JSONL_TargetTime_20261013.zip`, SHA256 `af521e0052028142549f6dbd220ca21bee3bfa1c32b6dfbb2c32eb7b1f171fdb`. Contains R24 immutable baseline, R07 frozen preview, 195/40 private join records, input ZIP SHA256 and source verifiers. The 55 MB original chat ZIP is **not included** and remains owner-provided.
- First replay: `R25_TARGET_MESSAGE_TIME_VERIFIED_195_JSONL_ONLY`.
- Independently extracted archive integrity verifier: `R25_PORTABLE_EVIDENCE_INTEGRITY_PASS_ONLY`.
- Integrity-only checks cannot independently reproduce source bytes without the private original uploaded ZIP.

**Next**: retrieve true request-effective card revision and mutation history for the two changed targets, restore the 132 training windows from source history with no invented facts, obtain independent content/age clearance, prove connected-world isolation and register genuinely new held-out groups. No train approval.
