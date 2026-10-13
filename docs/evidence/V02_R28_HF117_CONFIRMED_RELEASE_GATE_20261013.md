# StoryForge v0.2 — R28 verified HF117 report and final release blockers (2026-10-13)

**Formal training admission: `PENDING_NOT_APPROVED`; no GPU training launched.**

## 1. Independent remote engineering verification: PASS

GitHub private main HEAD before R28: `829ba128b4d66c6f58b3a6cbc2f1ca4e326e889c`, after the owner's R27 HF117 actual report LFS commit.

The dedicated [R27 report verification Action](https://github.com/sunxu/storyforge/actions/runs/38400578892) completed SUCCESS. It downloaded **actual Git LFS bytes** of the R27 report and the R27 frozen candidate archive, and ran `scripts/v02_verify_r27_hf_report.py`. Output:

- State: `R27_REMOTE_REPORT_INTEGRITY_VERIFIED_ONLY`.
- HF Job: `6ace19935ccb47ba0f787af5`.
- Report SHA256: `e23f166226142e28a04f42a3d481776b6ac84d9b30f92e30a55de838e5d2b213`.
- Frozen private candidate JSONL SHA256: `cdecc311f05e2c700f1038f3afca09c889ff681d4ef55dc18dc7426c9d14a92a`.
- **117 distinct candidate results from 11 distinct source-story UUIDs**; all report `ACTUAL_LAST_ROUND_INTERNAL_PASS` against the installed `ms-swift==4.5.3` / pinned Qwen tokenizer.
- ms-swift tokens: min **480**, max **3,694**, total **216,497**; Transformers view max **3,760**; supervised tokens total **30,517**.
- **117/117 renderer input IDs are not identical.** This is a known cross-renderer difference, not by itself an observed label leak; final training must preserve the audited ms-swift stack and semantics.
- No training performed by R27. Per-token full original labels are not embedded in report JSON, so the Action validates reported hashes/counts and mapping, not a separate re-encoding run.

The previously archived private source LFS backups and R27 report are recoverable at this HEAD. Separate private LFS archive workflow was successful.

## 2. R28 independently checked input structure

From the original private R27 archive (SHA256 `cfedf6935babd12c9fc214b46dc2078381b55de9487afe25212bf54e8706794f`):

- 117 unchanged provisional target replies; 40 old visible previews plus 77 source-anchored predecessor-window derivatives.
- Exactly **662 User turns**, **662 Assistant turns**, **117 new generic System instructions**; **no empty User content**, **no cross-story identical non-System dialogue content ≥50 characters**, and all 117 final Assistant target SHA256s align with frozen metadata.
- 11 story UUID groups. Original proposed allocation: 96 Train rows in 9 groups; 21 Validation rows in 2 groups. It is **not an approved split**.
- Current R21 bounded review exists for 40 candidates, including 20 marked as needing additional attention. 77 restored inputs do not have an equivalent signed full-context review.

The exact-overlap check confirms none of these 11 story UUIDs equals any of the 19 v0.1 historical Train/Validation/Test story IDs; this is not proof against renaming, shared IP, linked characters, or semantic leakage.

## 3. No pre-GPU approval yet

The remaining blockers are substantive, not Token/Mask engineering:

1. A human-authenticated final policy/age/user-agency review for every selected train/validation example; exclude unresolved cases instead of rewriting Gold.
2. Explicit authorization for the **new generic System instruction/no-card training derivative**, or source-authoritative request-effective historical story-card text and retokenization. The R27 System instruction is synthetic and does not represent the original model-request prompt.
3. Proven story/world/character alias connected components and split isolation beyond exact UUID equality.
4. At least one genuinely **new, untouched** held-out story/component reserved prior to model selection; disclosed v0.1 test is not eligible.
5. Named final approval of Train/Validation allocation and a data-release certificate, checked against exact SHA256s; no silent override.

## R28 private handoff

`StoryForge_v02_R28_Final_Release_Preflight_20261013.zip` SHA256 `dbbc3f295c450c9b18e005f2b07864018e6a22a02cf064a23bbe0c75ed6b5aab` contains 117 ID-level pending decisions, the still-blocked human release certificate, an offline release gate that cannot launch training, the real HF117 aggregate report hashes and an integrity verifier. It contains no new copies of raw story dialogue. `R28_READ_ONLY_EVIDENCE_AND_PENDING_STATE_PASS_ONLY` succeeded; intentional status tampering was rejected.

**Result:** Actual HF117 engineering audit has succeeded. Formal production SFT release remains `PENDING_NOT_APPROVED` for content/split/heldout/derivative contract, and paid GPU training must not start automatically.
