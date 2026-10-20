# StoryForge R52 — R45 historical exposure impact by world and target

**2026-10-20 — Strong R45 source-overlap evidence; no world signoff or admission.**

Owner R52 seven-world historical exposure screen, including the immutable private original R45 ZIP, returned `R52_SEVEN_WORLD_HISTORICAL_EXPOSURE_SCREEN_COMPLETED__SEMANTIC_HOLD` with:

- **29** R45 Train49 and **13** R45 Validation15 *rows* exactly sharing an R52 story UUID. They are not 42 distinct worlds.
- **537** normalized text evidence witnesses: **273** exact long messages, **264** sampled 120-codepoint fragment witnesses. They are not 537 separate contaminated training examples.
- Verified R45 Train SHA256 `e7442993088617c4eaefd3a0c9efc7651932f7048f34586046bf6d5b5981a742`; Validation SHA256 `5ebbb3c6986a5ac4d294175bab1980ee61df08536f9b8438c8a67010630f1963`; original ZIP SHA256 `da4b7718f1c1cbd0429553b684eeaf70f207fd2e41aae4e8fe0a52a11b647b9e`.
- Gold87 and v0.1 Train/Val/Test had zero identical story UUIDs and zero long-text witnesses in their separate limited screen. This does **not** prove semantic independence.
- **21/21** independent full-source inter-R52 world-pair reviews finished (87 citations) but seven-world owner graph remains **HOLD**.
- **46** R52 no-card target-quality first-pass possibles; **16** quality-HOLD cases; **Train 0 / Val 0 / No GPU**, R50 sealed.

## Next: deduplicate 537 witnesses and quantify the 46-case exposure

The new `scripts/v03_r52_r45_exposure_impact.py` performs an owner-local, read-only evidence reconciliation. It:

1. Revalidates existing 21-pair graph and historical-exposure safe receipts, frozen original R45 ZIP SHA, all seven original story body SHA hashes and the exact **537** indexed historical witness records.
2. Ephemerally extracts R45 Train49/Val15 JSONLs into a temporary 0700 directory after validating their immutable exact-file SHA and number of records; replay-computes the R45-only 537 witnesses from scratch and demands byte-for-byte JSON object equality with the previous witness set.
3. Computes distinct **world UUIDs** appearing in R45 Train, Validation, both and neither; preserves historical row ordinal citations privately.
4. Deduplicates text witnesses by message pair even when both long exact-message and fragment methods identified the same pair.
5. Maps the immutable **46** preliminary positive R52 target candidates to overlapping R45 world UUIDs; separately compares the SHA256 of each selected R52 target to the literal **last assistant target** from R45 Train/Validation when available.
6. Keeps model execution proof explicitly **false**. Even a Train49 UUID overlap doesn't prove which exact R45 records were in the R46 optimizer stream. To establish that, inspect actual frozen R46 source loader, dataset hash and run/job manifest.

On the Mac (source branch, all previously generated private files retained):

```bash
cd ~/workspace/storyforge
git switch audit/r49-r50-source-intake-20261015
git pull --ff-only

d="$HOME/.local/share/storyforge"
R45_ORIGINAL_ZIP="/absolute/private/path/to/owner-preserved-r45-original.zip"
install -d -m 700 "$d/r52/r45_impact"

python3 scripts/v03_r52_r45_exposure_impact.py \
  --source-zip "$d/r52/remaining18/R52_REMAINING_18_FULL_ORIGINAL_WORLD_REVIEW_PRIVATE.zip" \
  --r45-original-zip "$R45_ORIGINAL_ZIP" \
  --history-dir "$d/r52/history_exposure_with_r45" \
  --graph21-dir "$d/r52/graph21" \
  --post-quality-dir "$d/r52/post_quality" \
  --out-dir "$d/r52/r45_impact"
```

Expected only upon successful actual Mac source replay:

`R52_R45_HISTORICAL_WORLD_IMPACT_RECONCILED__SEMANTIC_AND_MODEL_LINEAGE_HOLD`.

Private outputs (all **0600** under owner-local **0700** directory; do not commit):

- `R52_PRIVATE_07_R45_WORLD_EXPOSURE_IMPACT.jsonl`: each world UUID, 29/13 source-row ordinals as appropriate, exact source-message evidence counts and missing signoffs.
- `R52_PRIVATE_46_R45_CASE_EXPOSURE_IMPACT.jsonl`: 46 frozen candidate identifiers/target SHA256 values, whole-story R45 source split overlap risk, and literal target-SHA reuse flags. Every row still `PENDING_NOT_APPROVED`; no assigned Train/Val.
- `R52_R45_WORLD_EXPOSURE_IMPACT_SAFE_AGGREGATE.json`: **safe count-only summary** (distinct Train/Val/union worlds, 46 target risk bins, deduplicated text message hits, exact target SHA matches and hard HOLD declarations).

No trained model, R50 sealed answers or network services are accessed. A long fragment match and identical dialogue from the same R45 source record may be recorded as two witnesses but only **one** unique pair in the impact report. A world overlap with R45 Validation is an evaluation exposure risk, not proof of R46 training exposure. Source scan positives are a reason to review the historical lineage and new heldout suitability, not automatic rejection of author-owned training data.

**Next after the safe result:** decide which worlds are already in the actual trained model's data ancestry, which are only past evaluation sources, and which could qualify as truly independent new validation worlds. Independently review human character-alias/setting ties and 46 candidate final quality/safety. R50 remains sealed. Absolutely no Train/Val/GPU without explicit subsequent owner signing.

Synthetic-only code CI: https://github.com/sunxu/storyforge/actions/runs/39413586965


## Owner-local diagnostic — R45 archive outer SHA mismatch (2026-10-20)

If `R52_R45_IMPACT_HOLD__R45_ORIGINAL_ZIP_HASH_CHANGED` occurs with the original impact script, the failure happens **before** the 537-witness replay, not after substantive target comparisons. The original error combined a missing/symlinked path and a mismatched whole-ZIP SHA256. Updated implementation distinguishes `R45_ORIGINAL_ZIP_MISSING_OR_SYMLINK` and `R45_ORIGINAL_OUTER_ZIP_SHA256_NOT_PINNED`. It continues to **require the same immutable original ZIP SHA256**, `da4b7718f1c1cbd0429553b684eeaf70f207fd2e41aae4e8fe0a52a11b647b9e`. Train49/Val15 *members* additionally must match their frozen SHA256. A re-packaged ZIP is **not automatically authorized** merely because its filename looks right.

Safe local check:

```bash
R45_ORIGINAL_ZIP="/path/to/the/exact-original-R45-zip-used-in-the-prior-successful-screen"
if [[ ! -f "$R45_ORIGINAL_ZIP" || -L "$R45_ORIGINAL_ZIP" ]]; then
  echo "R45_ZIP_MISSING_OR_SYMLINK"
else
  shasum -a 256 "$R45_ORIGINAL_ZIP"
fi
```

Copy the *exact unchanged original* R45 ZIP path from the previous `--r45-original-zip` command to the impact invocation; do not change the expected hash or edit/repackage the archive just to turn HOLD into a pass. If the original ZIP cannot be recovered, preserve HOLD and first compare frozen member SHA256 against an alternative archive as a separate explicit source-provenance action.

The latest fix also compares all 537 original witness dicts as a canonical multiset, not a process-dependent list ordering: Python hash-set iteration can vary between the two separate commands, but unchanged content must validate. Synthetic regression suite: https://github.com/sunxu/storyforge/actions/runs/39414475982.
