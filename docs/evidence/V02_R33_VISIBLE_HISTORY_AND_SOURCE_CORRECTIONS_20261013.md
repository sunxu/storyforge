# StoryForge v0.2 — R33 full R27 visible-history review and source correction

**Checkpoint:** 2026-10-13. **Training admission:** `PENDING_NOT_APPROVED`. Neither the immutable 87+108 curator Gold nor the R27 117-row provisional derivative has been rewritten or promoted. No GPU train was launched.

## Review scope achieved

- Started from the unmodified R32 ZIP SHA256 `bdd9bdde58fc6b670daba7ec94f50b4d73a1c5802a73e3cebc0571eb65519a3e`.
- Read **49/49** previously pending complete R27-visible histories (all preceding User/Assistant messages and the full final Gold target), with an individually linked current-User/target digest, history hash, reviewer note and literal evidence offset in the **private R33 ZIP**.
- Cumulative coverage for the **92 non-IP** records is now **71** complete R27 visible-history readings (22 R32 + 49 R33), with **21** prior R31 selected-turn/full-target bounded reviews still not at equivalent full-history depth.
- The other **25** R30 origin/IP-quarantined candidates remain unopened and isolated. No content/age policy approvals issued, no split or unseen heldout signed.
- Eight R33 cases have specific follow-up tags, including history-inserted player speech (2), repeated crowning, time discontinuity, player-action insertion, coercive history, an ingredient inconsistency (tomato-and-egg vs tofu), and relationship age/consent uncertainty. **Historical unsupervised Assistant defects are separated from final Gold target defects**. The other 41 had no newly substantiated *visible-window target hard error*, not approval.

## Important correction of earlier false-positive reasons

The owner-uploaded original conversation JSONL ZIP SHA256 `050af7034f9b2f3ef0401542364d23ef6ce126dd1699a49b1124d69245c98fdb` confirms concrete User-side prior context in the same source story:

- `virgin-death-gold-t01860`: source User turn **1847** explicitly locates the upcoming social event as a yacht event.
- `bh-gold-t0578`: source User turns **567 and 569** express that the action can start immediately.
- `bh-gold-t2404`: source User turn **2393** states reassurance for the family dinner.

These source User statements overturn interpretations that the **full original story** lacked the above facts. Critically, the **R27 short training input did not contain the corroborating User text** for these three cases. Do **not** conclude the unchanged provisional training samples now have adequate visible fact support; keep a `window-specific missing premise` decision pending, restore a verifiable prefix if approved, or exclude without modifying Gold.

## Integrity and deliverable

Private ZIP: `StoryForge_v02_R33_Full_Visible_History_20261013.zip`, SHA256 `57cfea5f921ca7b91329c5f24f24df6dcbd35ea49df92af9713ee38b7a891fd4`. It includes immutable R32 and R27 baselines, 49 detailed evidence rows, four original User turn witnesses for the three correction cases, cumulative 117-route status, `r33_gate.json`, `verify_r33.py` and `SHA256SUMS.txt`. Replaying the verifier against the original raw ZIP returns `R33_ORIGINAL_SOURCE_CORRECTIONS_REPLAY_PASS`; independent unzip integrity verification also passes. Intentional modified witness test returns exit 2, BLOCKED.

This GitHub document intentionally contains **no original private chat text**. Source quotes live only in the user-delivered private audit ZIP and pre-existing protected LFS sources. The portable archive consistency verifier does **not** establish actual historical model-request prompt identity, full canonical story ages, or final training safety.

## Next remaining gates

1. Complete equivalent full-visible-history review on **21** remaining non-IP records and adjudicate previously proposed Holds with **visible-input** requirements.
2. Determine approved handling of the three corrected-but-window-missing historical facts.
3. Final age/content/user-agency signoff; investigate or exclude 25 quarantined provenance/IP items rather than auto-clearing.
4. Prove linked-world/alias component isolation, reserve a genuinely independent never-exposed heldout population, and sign final Train/Validation splits.
5. If the final derived **bytes** differ, rerun the real Token/Mask gate. The historical R27 HF117 result remains valid only for **unchanged** provisional bytes.

**Formal status `PENDING_NOT_APPROVED` and zero approved Train/Validation/Test rows.**