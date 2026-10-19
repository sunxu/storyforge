# R51 Gold195 — metadata-based private triage (2026-10-19)

Source pinned to PR #2 HEAD `cfb9f4d0530eb5af3895f4fab2a81766b4e814d3` before this implementation commit. This is **real frozen source metadata inspection**, not full transcript replay, training admission, or per-row human review.

## Observed cross-tabs (195 original selected rows)

| Mutually exclusive flag set | Count |
|---|---:|
| Explicit card/timepoint evidence UNVERIFIED only | 161 |
| Card UNVERIFIED + age UNSPECIFIED | 10 |
| Source index fields absent only | 22 |
| None of these three explicit flags | 2 |
| **Total** | **195** |

171 card markers, 22 source-index metadata gaps and 10 unspecified ages. The 10 unspecified ages are all in story rank 04 and overlap the card-marker group; no source-index gap overlaps those 171 markers. **193/195** have at least one of the three explicit flags, but the other two are **not** certified. These are metadata-level patterns, not proof of historical card necessity or consent/rights clearance.

Important: 22 records lack the *two examined direct index fields*, not necessarily all transcript identifiers. Some rows have source turn/archive metadata, which may permit authenticated reconciliation later. Preserve source format differences; do not backfill the Gold originals.

## One private, actionable workpaper

Local-only command on the authorized Git checkout:

```bash
install -d -m 700 ~/.local/share/storyforge/r51
python3 scripts/v03_r51_gold195_private_triage.py \\
  --repo . \\
  --output ~/.local/share/storyforge/r51/R51_GOLD195_PRIVATE_TRIAGE_v1.jsonl
```

The command verifies frozen cohort SHA and selection index using the existing readiness implementation. It creates **195 private, versioned candidate rows** with candidate and source identities, original target digest, history-message fingerprints, explicit metadata-risk flags, evidence placeholders and two-reviewer fields; write mode is 0600 with exclusive creation. The parent directory must be private (0700); a Git-tree output is rejected. Original chat, target prose, raw reviewer reasons and identifiers do **not** go into the count-only stdout or any new tracked file.

Each row starts at `PENDING_NOT_APPROVED`, `split=null`, with `CONTENT_OR_RIGHTS_HOLD`; the 22 direct-index gaps also receive `SOURCE_POINTER_RECONCILIATION_HOLD`. Card/timepoint uncertainty remains a distinct evidence flag. **The script deliberately does not infer `CONTEXT_ONLY_POSSIBLE__HOLD` or `CARD_OR_LONG_RANGE_SOURCE_REQUIRED__HOLD` from metadata alone**: the route stays `UNDECIDED__SOURCE_ANCHORED_REVIEW_REQUIRED` until a reviewer verifies actual context sufficiency and historically available facts.

## Next review operation, not a new audit-loop

For each candidate, use authenticated original source chat with target-point cutoff to resolve pointers and contiguous history, determine local context-only sufficiency versus historical card/long-range dependency, then check age/consent/rights/forbidden rules and player autonomy. Record evidence references and two independent source reviewers in the private workpaper. Final component-disjoint Train/Val assignment requires verified linkage across stories, frozen older tests and R50, and separate engineering loss-mask checks.

R45 18 HOLD unchanged; W17 frozen; R50 test text untouched; no HF/GPU, model promotion, final seal or PR merge. The metadata screening output is not a new R51 content or training PASS.


## Owner declaration received on 2026-10-19 — age, consent, content limits

The project owner stated in the R51 continuation conversation that they
have confirmed **age, consent and content-boundary compliance** for the
candidate material. Record this as **OWNER_ATTESTED__2026-10-19** for the
Gold195 admission work, not as an independently source-replayed per-row fact,
legal opinion, training-data license grant or a final model-input approval.

The ten original `source_character_age=UNSPECIFIED` metadata values remain
unchanged, because a later owner declaration does not retroactively add
historical source metadata. Their review follow-up becomes
`OWNER_ATTESTED__SOURCE_METADATA_UNSPECIFIED`, not an automatic safety
or source-chronology PASS. Avoid repeating a generic request for the
owner to confirm age/consent/content limits unless specific contradictory
source evidence arises.

The local private 195-row worksheet v1 has been reported successfully
created with status `R51_PRIVATE_GOLD195_HOLD_WORKPAPER_CREATED__NO_ADMISSION`.
Its existing `source_review.age_and_consent=PENDING` records are historical
pre-declaration state; preserve v1 and record the owner declaration in a
new **local-only** worksheet version. Do not change Gold originals, silently
delete source-risk flags, upload candidate IDs or raw private review notes
to Git/CI, or claim individual source-anchored reviews have occurred.

**Remaining substantive blockers:** authenticated original-source pointer
reconciliation for the 22 direct-index gaps, context-only vs long-range/card
dependency backed by actual original conversations and target-time evidence,
training-use rights/licenses beyond the owner's age/consent/content assertion,
player-agency and rule compliance, independent source review, semantic
world-component segregation from frozen older tests/R50, and eventual
CPU tokenizer/collator loss-mask verification. All 195 remain
`training_admission=PENDING_NOT_APPROVED`, `split=null`;
`CONTENT_OR_RIGHTS_HOLD` remains until its other grounds are resolved.
No GPU/HF/inference/merge/promotion/seal is authorized by this declaration.
