# StoryForge v0.2 — R34 final 21 full R27-visible histories (2026-10-13)

**Formal training admission: `PENDING_NOT_APPROVED`.** No GPU training job was started. The two immutable curator Gold cohorts (**87 + 108 = 195**) and the provisional R27 candidate JSONL (**117 rows**) remain byte-identical.

## Review work completed

R33 left **21** non-IP samples with only selected-turn/full-target reading. R34 read all **21/21** complete **R27-visible** User/Assistant turns in sequence and the complete final Gold target. Each R34 row stores source candidate ID, story UUID, role, exact quotation with string offset, per-message/target SHA256, narrative assessment and a *nonapproved* derivative recommendation.

Earlier R32 **22** + R33 **49** + R34 **21** = **92/92** non-IP candidates with **complete R27-visible context reading coverage**. The **25** source/IP-origin-quarantined samples remain excluded and were not reopened. This reading scope does not authenticate the original model request, historical hidden card, target-time age or IP permissions.

Review observations include previously unsupported facts in *historical* Assistant messages, school-age uncertainty, relationship coercion, grief/self-harm framing, and a potential unsupported fictional dungeon reset rule. These are candidate-specific concerns, not wholesale declarations that supervised Gold targets are wrong. No new final age/content approval was granted.

### Earlier source correction versus training-window leakage

The owner-supplied original User history confirmed earlier statements for:

- `bh-gold-t0578` — earlier User turns 567 and 569;
- `virgin-death-gold-t01860` — earlier User turn 1847;
- `bh-gold-t2404` — earlier User turn 2393.

These facts correct prior claims that the *entire original story* lacked the statements. **The R27 shorter derived input does not contain the necessary User premise**, so the two cases revisited in R34 retain the **previously recommended** window-premise HOLD, and the third retains the prior review recommendation. This does **not** add new HOLD counts, nor does it change the frozen Gold.

A distinct example, `s08-gold-t00012`, responds to a User challenge about an earlier unsupported photoshoot booking by acknowledging possible confusion. Preserve the difference between the earlier Assistant's claim and the target's correction.

## Exact reproducibility

- R27 input SHA256 `cdecc311f05e2c700f1038f3afca09c889ff681d4ef55dc18dc7426c9d14a92a`.
- Unmodified R33 parent archive SHA256 `57cfea5f921ca7b91329c5f24f24df6dcbd35ea49df92af9713ee38b7a891fd4`.
- R34 private evidence ZIP SHA256 `0b07207725d0f129a6b5e906c4a029efeca532ab1edd43f4ea6e2d4dfdef8abd`.
- Read-only `verify_r34.py` checks all 21 quotation locations, 21 target hashes, 117 inherited cumulative route fields, 92/25 coverage counts and nonapproval gate.
- Portable check: `R34_21_FULL_VISIBLE_HISTORY_EVIDENCE_REPLAY_PASS__92_92_NON_IP_COVERED__TRAINING_BLOCKED`. Intentionally altered witness text was rejected.
- The R34 ZIP contains verbatim private dialogue snippets and nested R33/R27 archives. **Do not commit it as ordinary Git source**; this documentation and separate aggregate gate JSON contain no private excerpts.

## Still mandatory before a full paid GPU SFT

1. Individual final full-context policy/age/player-agency decisions and exclusions as appropriate. **0 formally signed content approvals**.
2. Separate provenance/IP review of 25 isolated samples; no automatic restoration.
3. Prove cross-story/alias/linked-IP component isolation and sign Train/Validation components; **0 approved rows**.
4. Acquire and preregister a genuinely **new, sealed, not-yet-scored** held-out story set; **0 such components are available**.
5. User has authorized the *generic no-character-card experiment definition*, not training of any unresolved examples or an automatic GPU purchase.
6. Actual R27 HF `last_round` 117/117 remains valid for the **unchanged** candidate bytes. Adding missing context or removing/recompiling examples calls for a new final-input provenance check and, if prompts change, a real Token/Mask check before formal approval.

**Result: all 92 non-IP R27-visible histories have been reviewed, but formal training admission remains `PENDING_NOT_APPROVED`.**