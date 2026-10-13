# StoryForge v0.2 — R32 full-target review with bounded historical depth

**Date:** 2026-10-13. **Formal training admission:** `PENDING_NOT_APPROVED`. No GPU job was submitted; frozen original 195 Gold, source-anchored R27 117-row derivative, R30 generic no-card input design, previous holds and R31 recommendations all remain unchanged.

## Exact review scope

R31 had left 71 of the 92 non-IP candidates with only current User and the opening of the Gold target inspected (21 had deeper selected-turn/full-target review). R32 extended **all 71/71** remaining candidates to full reading of the immediate User input and the *entire* final Assistant target; all prior message-turn openings were inspected.

- **22/71** additionally received a full-length reading of all visible R27 preceding messages.
- **49/71** did **not** receive that full-length prior-history reading. Do not label these as complete story/history audits.
- The 25 prior source/IP quarantine records were not rereviewed.
- Read-only evidence contains 71 user/target quote/hash pairs, 117 full cumulative per-ID routing states, and 12 exact-quotation issue witnesses covering 11 IDs. A source issue may belong to **earlier unsupervised Assistant history**, not the Gold target.
- **0** formal age/content approvals, **0** approved Train/Validation/Test assignments, and **0** genuinely fresh sealed held-out stories.

## New source-anchored priority observations

The following are *recommendations/unknowns*, **not final policy violation or independent adjudications**:

- `bh-gold-t2404`: target mentions “刚才某人许下的承诺最好算数”, while no such promise occurs in the R27 visible User turns; earlier off-window source may still exist. Needs history proof or quarantine.
- `s15-gold-r02-t01460`: prior Assistant places a crown on the player even though User already says the crown was worn; this is a preceding-history continuity issue. The target separately announces a named new arrival whose earlier canon is not proven.
- `s15-gold-r02-t02000`: preceding Assistant begins “——次日黄昏。” after a visible return-to-palace dinner request. Needs storyline chronology check; not necessarily a direct Gold-target failure.
- `sf14-gold-t00746` / `s14-gold-r02-t02020`: original dialogue shows alcohol in one scene and school-vacation context in the same story corpus. Effective character ages and whether the participants coincide remain unproved. School involvement does not by itself prove age below 18.
- `bh-gold-t0801`, `na-gold-t0195`, `s09-gold-r03-t02889`: previous Assistant narration attributes User gestures/reactions without clear previous-User source; assess prompt-contamination/player-autonomy risks separately from Gold-target merits.
- `s06-gold-t03412`: previous Assistant obstructs a player's attempt to get out of bed; relation/agency context requires review.
- `s06-gold-t01355`: previous User requested a status panel update; needs prior-turn instruction-following review.
- `virgin-death-gold-t03176`: Gold target uses extreme self-blame language in a relationship; contextual style/safety review needed, not automatically disallowed.

The R31 recommendations `bh-gold-t0578` and `virgin-death-gold-t01860` remain unchanged and **must not be silently promoted**.

## Private audit package and verification

Private ZIP: `StoryForge_v02_R32_Full_Target_Bounded_History_20261013.zip`; SHA256 `bdd9bdde58fc6b670daba7ec94f50b4d73a1c5802a73e3cebc0571eb65519a3e`. Unmodified R31 parent SHA256 `085ddc99926b7296752448c1872de33f90441121a82192a9263bb71ee8b7a390`. Fixed R27 source JSONL SHA256 `cdecc311f05e2c700f1038f3afca09c889ff681d4ef55dc18dc7426c9d14a92a`.

The independent extracted R32 verifier confirmed all 71 current User / full target hashes and offsets, 12 issue quotation offsets, 117 unchanged target hashes, scope arithmetic and explicit `PENDING_NOT_APPROVED`; intentional quotation tampering returned exit code 2. Terminal marker: `R32_71_FULL_TARGET_22_FULL_VISIBLE_HISTORY_49_HISTORY_PENDING_EVIDENCE_PASS_ONLY__NO_TRAINING_APPROVAL`. Integrity verification does not prove the reviewer actually read all material, narrative safety, license rights, or model-original prompt reconstruction.

The R32 ZIP nests confidential R31/R27 source content. Do **not** commit it to GitHub as ordinary text; this public-of-repo-but-private-to-members documentation contains no private excerpts beyond minimal cited dialogue fragments.

**Next:** prioritize complete prior-history reading for 49 candidates; adjudicate the source-specific proposed holds while keeping historic prompts and Gold unmodified; resolve source/IP/age policy, cross-world component splits and genuinely unexposed heldout. The audited HF 117/117 Token/Mask result remains valid for unchanged R27 bytes, but is not a training release.