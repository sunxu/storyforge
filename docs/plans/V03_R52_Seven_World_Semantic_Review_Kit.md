# R52 — Seven source stories / twenty-one bounded world-link reviews

**No admission, no train/validation split, no paid GPU, no R50 sealed heldout access.**

## Current verified starting point

Owner ran `scripts/v03_r52_world_exact_isolation.py` locally and reported
`R52_V01_EXACT_UUID_SCREEN_PASS__WORLD_GRAPH_AND_SEALED_TEST_HOLD`:

- R52 post-quality: 62 decisions and 205 citations, **46 first-pass feasible**, **16 quality HOLD**, **7 source-story UUIDs**.
- Exact UUID overlap of R52 seven source stories against SHA256-verified frozen v0.1 Train (65 rows), Validation (15 rows), and Test (20 rows): **0 for all three**.
- Semantic/world graph status: **0 reviewed**; **0** confirmed independently isolated world components; **0** Train/Val assignments.
- Existing Gold87 contains known v0.1 Train overlap and must not be merged automatically. The historical 04↔07 linked-world relation must continue to be treated as a component issue if present in eventual source population.

No historical point-in-time character/system card has been recovered by these screens. The generic no-card experiment evaluates a **new task contract**, not the original source-model prompt.

## Build bounded independent world-link review tasks

From the owner's Mac audit branch:

```bash
cd ~/workspace/storyforge
git pull --ff-only
d="$HOME/.local/share/storyforge"
install -d -m 700 "$d/r52/world_review"

python3 scripts/v03_r52_world_semantic_review_kit.py \
  --prepare \
  --world-dir "$d/r52/world_isolation" \
  --post-quality-dir "$d/r52/post_quality" \
  --private-packets "$d/r51/R51_GOLD108_PRIVATE_CONTEXT_REVIEW_v1.jsonl" \
  --out-dir "$d/r52/world_review"
```

Expected marker:
`R52_SEVEN_WORLD_TWENTYONE_PAIR_REVIEW_TASKS_PREPARED__NO_ADMISSION`.

The script:
1. Validates all **108** source packets, their frozen visible message body SHA256 and target body SHA256.
2. Pins the previously verified 7-source-story world-identity queue and the 46-case first-pass shortlist.
3. Builds **7** owner-private source dossiers with **up to 2** representative frozen target/visible message excerpts per story, exact index and original SHA256.
4. Creates **21** pairwise story-world review tasks and a blank **21-row** decision template.
5. Never includes earlier source preview as model input, never substitutes export-time card snapshots for historical prompts, and never assigns training status.

Files (private directory 0700, individual JSONL 0600):
- `R52_PRIVATE_07_WORLD_DOSSIERS.jsonl`
- `R52_PRIVATE_21_WORLD_PAIR_REVIEW_TASKS.jsonl`
- `R52_PRIVATE_21_WORLD_PAIR_DECISION_TEMPLATE.jsonl`
- `R52_WORLD_SEMANTIC_KIT_SAFE_AGGREGATE.json`

**Important scope limitation:** Dossiers contain *two bounded examples per world*, not full original stories. Even 21 reviewed pairs with no observed match do **not** certify absence of shared-world aliases or prior v0.1 semantic exposure. Negative evidence in this narrow source sample must remain HOLD. The sealed R50 independent tests must stay sealed.

## Independent review instructions

Give an independent reviewer only the private 21-pair task file, not prior R51 A/B/C quality votes or old pair review answers. For every pair the reviewer must choose **one**:

- `LINKED_WORLD_EVIDENCE__HOLD`: evidence suggests shared persona, world, character identity, unique locale, event, rules or narrative dependency.
- `NO_LINK_OBSERVED_IN_BOUNDED_EVIDENCE__HOLD`: no link found within the **provided bounded samples**, *not* proven independence.
- `INSUFFICIENT_SOURCE_EVIDENCE__HOLD`: samples too narrow or ambiguous to decide.

For each of 21 decisions, retain `schema=storyforge-r52-private-world-pair-decision-v1`, the exact `left_rank` / `right_rank`, matching pair target-digest pins, `training_admission=PENDING_NOT_APPROVED`, `reviewer_a_b_analysis_seen=false`, a 30+ character source-grounded rationale and `source_citations` with exact `scope`, `story_rank`, `original_source_array_index`, `source_body_sha256`. Link or bounded no-link judgments require citations from **both** stories; insufficient-source judgments may cite one side or none. **No invented evidence.**

Save the completed **separate** file `R52_PRIVATE_21_WORLD_PAIR_DECISIONS.jsonl` in the same private directory. Preserve the original blank template and tasks.

Validate (not an authorization):

```bash
python3 scripts/v03_r52_world_semantic_review_kit.py \
  --validate \
  --world-dir "$d/r52/world_isolation" \
  --post-quality-dir "$d/r52/post_quality" \
  --private-packets "$d/r51/R51_GOLD108_PRIVATE_CONTEXT_REVIEW_v1.jsonl" \
  --out-dir "$d/r52/world_review" \
  --decisions "$d/r52/world_review/R52_PRIVATE_21_WORLD_PAIR_DECISIONS.jsonl"
```

Expected `R52_21_WORLD_PAIR_REVIEWS_VALIDATED__GRAPH_STILL_HOLD`. Validity means **21 source-grounded results**, not 21 proven isolated world pairs.

## Final release gate after pair review

The owner must examine **full original story/card source evidence** for any possible linked-world groups, perform cross-comparison with Gold87, historical v0.1 exposure and sealed test components without unsealing R50 answers, then sign a linked-component map. In a separate step, sign target-specific ages/consent/content and final quality decisions for the 46 candidates. Only after those gates can a world-component-disjoint Train/Val proposal be evaluated, along with an exact pinned no-card system prompt, tokenizer length and final-target-only ms-swift labels. No GPU before explicit authorization.

This workflow never changes Gold195, R51 adjudications or R52 Batch 01–04 decisions.


## Owner-validated 21-pair bounded semantic review (2026-10-20)

Owner ran `scripts/v03_r52_world_semantic_review_kit.py --validate` against private, frozen decisions, obtaining `R52_21_WORLD_PAIR_REVIEWS_VALIDATED__GRAPH_STILL_HOLD`.

- **21/21** pairs with **126/126** authentic citations passed validator.
- Routes: **18** `NO_LINK_OBSERVED_IN_BOUNDED_EVIDENCE__HOLD`, **3** `INSUFFICIENT_SOURCE_EVIDENCE__HOLD`, **0** `LINKED_WORLD_EVIDENCE__HOLD`.
- These outcomes **do not certify independence**. The three insufficient pairs are prioritized for *full-original-source* examination; the 18 other pairs remain unverified beyond their bounded source slices.
- **No Train/Val assigned**, **Train 0 / Validation 0**, **no GPU**, **sealed R50 not accessed**. All original source and private pair rationales remain outside Git.

Next: use the R51-authenticated source archive and original full message histories to collect per-world original-source evidence, including the three priority pairs, then undertake owner source/quality/safety signoff. A bounded no-match vote must not be used as a substitute for the source-complete graph gate.


## 2026-10-20 — 21-pair review validated, full original source recovery

Owner verified all 21 bounded pair decisions and 126 evidence citations. Route totals: 18 bounded no-link HOLD, 3 insufficient-source HOLD, 0 observed links. This does not certify world independence.

The next script `scripts/v03_r52_full_original_world_recovery.py` replays the 06–15 source LFS archive and the R51 original target/history SHA256 provenance before producing **seven owner-private complete original source files**, all **21** full-source review indexes and **three** priority follow-up indexes. A synthetic-only CI passed: [Actions 39387903307](https://github.com/sunxu/storyforge/actions/runs/39387903307). Real owner full-source replay has not run yet.

Local command (audit branch, original LFS ZIP already pulled):

```bash
cd ~/workspace/storyforge
git pull --ff-only
d="$HOME/.local/share/storyforge"
install -d -m 700 "$d/r52/world_full"
python3 scripts/v03_r52_full_original_world_recovery.py \
 --repo . \
 --private-packets "$d/r51/R51_GOLD108_PRIVATE_CONTEXT_REVIEW_v1.jsonl" \
 --post-quality-dir "$d/r52/post_quality" \
 --world-dir "$d/r52/world_isolation" \
 --bounded-review-dir "$d/r52/world_review" \
 --out-dir "$d/r52/world_full"
```

Expected only after complete original evidence validation: `R52_SEVEN_COMPLETE_ORIGINAL_STORIES_RECOVERED__ALL_21_GRAPH_HOLD`. Return only `R52_FULL_ORIGINAL_WORLD_RECOVERY_SAFE_AGGREGATE.json` to project tracking. Never commit the private complete story files. Actual historical point-in-time story cards remain unproven; export-time cards are not original prompts.

Next: source-grounded human review of three priority pair links (and then the other 18), full old Gold87/v0.1 semantic overlap and owner content/safety signoff. **All `PENDING_NOT_APPROVED`, Train 0 / Val 0 / No GPU; R50 sealed tests unopened.**


## 2026-10-20 — Seven full original world exports recovered (owner-local, no admission)

Owner supplied `R52_FULL_ORIGINAL_WORLD_RECOVERY_SAFE_AGGREGATE.json`, produced by the local source-pinned full-original recovery tool, with status `R52_SEVEN_COMPLETE_ORIGINAL_STORIES_RECOVERED__ALL_21_GRAPH_HOLD`:

- **7/7** complete story exports restored from pinned source archive SHA256 `b874cd07547092e9c3c967f69fab6b75262ff4f44ba2d368fd575f84e8886afb`.
- **20,577** original source messages indexed with source SHA256.
- **104** original R51 target/history pins reverified within those seven source stories. This is not 108/108 because the selected seven-world scope excludes the other original Gold108 story; no claim of missing or defective Gold108 records.
- **21** full-story pair-index tasks; **3** prioritized pairs originally flagged `INSUFFICIENT_SOURCE_EVIDENCE__HOLD`, **18** formerly bounded no-link pairs.
- **0** full-source semantic reviews, **0** linked-world components certified, **0** quality/admission signatures, **0** Train/Val assignments, **0** GPU jobs authorized; R50 sealed heldout unopened.

The next activity is to *review* the three prioritized full-source pairs, preserving all 21 graph edges as HOLD. A source integrity/recovery receipt cannot establish world independence by itself.


## R52 priority 3 full original source handoff (2026-10-20)

After the owner recovered **7/7 full original story exports** (20,577 original messages; 104 source-pinned R51 targets within these stories), the new `scripts/v03_r52_pack_priority_full_source_pairs.py` can **package the three unresolved pairs with their complete original story files** for an independent full-source reviewer. It verifies all 7 full story files, all 20,577 message SHA256 values, all 104 R51 target pins, the exact three priority edges against the full 21-pair queue, and the original source ZIP receipt. It then includes **only** the distinct story files required for the three priority pairs, with the priority tasks, README and a SHA256 manifest.

Run on the Mac, in the audit branch:

```bash
cd ~/workspace/storyforge
git pull --ff-only
d="$HOME/.local/share/storyforge"
install -d -m 700 "$d/r52/priority03"
python3 scripts/v03_r52_pack_priority_full_source_pairs.py \
  --repo . \
  --world-full-dir "$d/r52/world_full" \
  --out-dir "$d/r52/priority03"
```

Expected only after owner-local verification: `R52_PRIORITY_03_COMPLETE_SOURCE_PACKAGE_VERIFIED__GRAPH_HOLD`.

Private outputs (do **not** commit to GitHub):
- `R52_PRIORITY_03_FULL_ORIGINAL_WORLD_REVIEW_PRIVATE.zip` — three priority pair specs + their distinct complete original story files, source manifest and reviewer instructions.
- `R52_PRIORITY_03_FULL_ORIGINAL_WORLD_REVIEW_SAFE_RECEIPT.json` — count-only SHA256 validation and no-admission receipt.

No graph edge or story is certified independent by this *packaging* stage. After full original pair adjudications, the remaining 18 bounded no-link pair relationships must still undergo full-source coverage and owner component signing. The owner-retained ownership statement does not substitute for target content/safety and experimental SFT data gates. **Train 0 / Validation 0 / No GPU; R50 sealed set unopened.**
