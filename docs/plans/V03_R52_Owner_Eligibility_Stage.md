# R52 — Owner-attested Gold108 eligibility staging

**Status:** owner-confirmed rights at intake; content and historical-card gates still pending; **Train 0 / Validation 0 / No GPU**.

## Scope and decision

On 2026-10-20 the project owner explicitly confirmed ownership of **all StoryForge content**. R52 accepts this declaration as the project owner's source-use basis for proceeding to *eligibility review*, rather than repeatedly requiring the owner to prove ownership. The declaration is recorded locally as **OWNER_ATTESTED**, not misrepresented as an independent legal audit or as sample-by-sample permission to train.

This removes the outstanding *owner rights declaration* blocker. It does **not** automatically change any frozen R51 review, prove historical role-card version/timepoint, clear player-agency defects, establish target suitability, assign a world split, unlock R50 sealed heldout, or authorize GPU/HF training.

## Runnable local intake

From the project repository on the owner's Mac:

```bash
cd ~/workspace/storyforge
git pull --ff-only

install -d -m 700 "$HOME/.local/share/storyforge/r52"

# Owner confirms the explicit switch based on their statement in this chat.
python3 scripts/v03_r52_owner_eligibility_intake.py \
  --repo . \
  --post-c-register "$HOME/.local/share/storyforge/r51/reviews/R51_GOLD108_POST_C_RISK_REGISTER_PRIVATE.jsonl" \
  --private-packets "$HOME/.local/share/storyforge/r51/R51_GOLD108_PRIVATE_CONTEXT_REVIEW_v1.jsonl" \
  --out-dir "$HOME/.local/share/storyforge/r52" \
  --owner-attests-full-content-ownership
```

The script requires 0600 private input files and 0700 input/output parent directories, verifies exactly 108 unique candidates against the authentic frozen source-target SHA256, rechecks A/B/C route relationships, and creates files without overwriting existing ones. It emits only aggregate counts. All files containing candidate identities remain local and must **never** be committed.

## Expected local files

| Output | Count or purpose |
|---|---|
| `R52_PRIVATE_OWNER_RIGHTS_ATTESTATION.json` | Timestamped owner attestation; not external certification |
| `R52_PRIVATE_CONTEXT_62_QUALITY_CARD_QUEUE.jsonl` | 62 mutually context-sufficient A/B candidates; **not admitted** |
| `R52_PRIVATE_THREE_WAY_04_FOLLOWUP_QUEUE.jsonl` | 4 C≠A/B source/quality disputes |
| `R52_PRIVATE_OTHER_DISPUTES_10_HOLD_QUEUE.jsonl` | 10 remaining conflicting A/B cases (C aligns with one) |
| `R52_PRIVATE_LONG_RANGE_AGENCY_32_HOLD_QUEUE.jsonl` | 26 long-range/card plus 6 agency/rule holds |
| `R52_SAFE_ELIGIBILITY_INTAKE_AGGREGATE.json` | Count-only, safe to share |

All 108 queues preserve target hash, story rank, original source offset and frozen reviewer route positions. Every record has `historical_card_at_target_time=NOT_VERIFIED`, quality gates PENDING, `world_split=null`, and `training_admission=PENDING_NOT_APPROVED`.

## Next actionable qualification work (after intake)

1. **Source/card provenance:** for each of 62 context-only candidates, identify the role/world card **as it existed at the target turn**, and verify the target does not rely on contrary long-range rules. An observed current/export card is **not** sufficient proof for an earlier historical point.
2. **Target quality:** review actual target against R51 frozen-window evidence and focus on player agency, NPC-only decisions, chronological consistency, and special rules. Reviewer route agreement does not certify prose quality. Record explicit PASS/HOLD and traceable source evidence per candidate.
3. **World-isolated split:** only after quality/card decisions, assign entire stories to Train or Validation (not individual examples from the same world on opposite sides) and record story-level isolation; keep the R50 sealed heldout untouched.
4. **Release gate:** a separate owner-approved, source-cited admission manifest may be created only for cases passing card, target-quality, safety and world-split requirements. R52 intake alone never permits SFT/GPU.
5. **Separate old Gold87:** do not silently merge these 108 queues into the historic Gold87 without its own provenance and quality checks.

## Fail-closed behavior

A wrong source hash, missing record, changed A/B/C route status, nonprivate file or duplicated output causes `R52_OWNER_INTAKE_HOLD__<fixed error code>`. Do not edit original R51 review files to make a failure disappear; preserve all previous reviews and receipts.


## R52 Batch 01 no-card quality review — local validation (2026-10-20)

The owner reported successful local validation of `R52_NO_CARD_BATCH_01_QUALITY_RESULTS.jsonl` with `scripts/v03_r52_no_card_quality_reviews.py --validate --batch 1`:

- Receipt status: `R52_QUALITY_RESULTS_VALIDATED__NO_ADMISSION`.
- Completed and validated: **16/16** target-quality reviews, **50** source citations.
- Route counts: **11** `NO_CARD_CONTEXT_AND_TARGET_POSSIBLE__HOLD`, **2** `TARGET_PLAYER_AGENCY_DEFECT__HOLD`, **2** `TARGET_CONTINUITY_OR_FACT_DEFECT__HOLD`, **1** `HIDDEN_PREMISE_OR_CARD_DEPENDENCY__HOLD`.
- These are *review findings*, **not admission approvals**. All 16 remain `PENDING_NOT_APPROVED`. **Train 0 / Validation 0 / No GPU**.
- Remaining unreviewed in the 62-case R52 no-card quality track: **46** (batches 02–04: 16, 16, 14).
- Original Gold195 is unchanged. The owner-local decisions, target text, story identities and citations remain private, and are not committed to this repository.

**Next action:** owner prepares the existing batch 02 tasks from the same pinned 62-queue and 108 private source packets; quality review must use frozen visible input only, not historical-card reconstruction or prior source previews as model input.


## R52 Batch 02 no-card quality review — local validation (2026-10-20)

The owner ran the local `scripts/v03_r52_no_card_quality_reviews.py --validate --batch 2` against the 16 frozen private tasks and reported `R52_QUALITY_RESULTS_VALIDATED__NO_ADMISSION`.

- Batch 02: **16/16** validated decisions; **58** source citations; **12** `NO_CARD_CONTEXT_AND_TARGET_POSSIBLE__HOLD`, **2** `HIDDEN_PREMISE_OR_CARD_DEPENDENCY__HOLD`, **2** `TARGET_PLAYER_AGENCY_DEFECT__HOLD`.
- Batches 01–02 combined: **32/62** reviewed; **23** context/quality preliminarily possible, **4** agency defects, **2** target continuity/fact defects, **3** hidden-premise/card dependencies. **108** source citations across both batches.
- Batches 03–04 remaining: **30** cases (16 + 14).
- **All original cases remain `PENDING_NOT_APPROVED`; Train 0 / Validation 0 / No GPU.** The 23 preliminarily feasible cases are not approved and no split or promotion is authorized.
- The private source text, candidate IDs, and full rationales remain owner-local; this count-only checkpoint is safe for the repository.

Next step: prepare Batch 03 (16 cases) from the same owner-attested R52 62-queue and original private R51 packets, without replacing historical cards or altering Gold195.
