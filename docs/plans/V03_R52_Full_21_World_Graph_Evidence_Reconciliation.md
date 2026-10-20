# R52 — Full-source 21/21 world-pair result reconciliation

**Status 2026-10-20:** all 21 source-pair review decisions are available. Three priority pairs have their independent private SHA-anchored validation receipt; remaining Batch 01/02/03 each have the owner's formal `R52_REMAINING_18_BATCH_REVIEW_VALIDATED__GRAPH_HOLD` receipts. This stage re-verifies them together. It is not world-independence certification or train/validation admission.

## Reviewed evidence in scope

- Authenticated seven complete original story exports: 20,577 original messages, 104 R51 target source pins in these seven sources.
- Earlier priority source ZIP: **3** pair results, **15** full-original message citations, decision file hash `f9bdee7693fb2ed6f66babafb431c5e83b13185248cc95969c55976f126a0f36`. Its earlier validation receipt was independently produced; do **not** misrepresent this as a new owner execution unless owner later validates it themselves.
- Remaining 18 pair reviews with three **owner-formally validated** 6-pair receipts: **72** source message citations. Decision SHA256 pins are frozen individually for all three batches.
- All 21 full-original reviewer routes: `NO_LINK_OBSERVED_IN_FULL_AVAILABLE_SOURCE__HOLD`, not `WORLD_ISOLATION_PASS`.
- Seven source ranks: 06, 09, 10, 12, 13, 14, 15. Prior known linked story relation 04↔07 outside these seven remains a historic graph warning when integrating other cohorts.
- Original R50 heldout remains sealed, no Train/Val, no GPU.

## Mac: reconcile full 21 graph evidence

Use the same StoryForge audit branch and owner-private artifacts, not any files in public Git.

```bash
cd ~/workspace/storyforge
git switch audit/r49-r50-source-intake-20261015
git pull --ff-only

d="$HOME/.local/share/storyforge"
install -d -m 700 "$d/r52/graph21"

python3 scripts/v03_r52_reconcile_full21_world_graph.py \
  --source-zip "$d/r52/remaining18/R52_REMAINING_18_FULL_ORIGINAL_WORLD_REVIEW_PRIVATE.zip" \
  --source-receipt "$d/r52/remaining18/R52_REMAINING_18_SOURCE_PACKAGE_SAFE_RECEIPT.json" \
  --priority-decisions "$d/r52/priority03/R52_PRIORITY_03_FULL_SOURCE_WORLD_PAIR_DECISIONS.jsonl" \
  --priority-receipt "$d/r52/priority03/R52_PRIORITY_03_FULL_SOURCE_VALIDATION_RECEIPT.json" \
  --remaining18-dir "$d/r52/remaining18" \
  --post-quality-dir "$d/r52/post_quality" \
  --out-dir "$d/r52/graph21"
```

If the two Priority03 files were not copied to the owner's `priority03` folder, retrieve them from the previously handed-off `R52_PRIORITY_03_FULL_SOURCE_REVIEW_VERIFIED_PRIVATE.zip`, outside the Git repository, then set `chmod 600` on the two files. Do not alter SHA256 pins, original story source, target text or decisions merely to bypass an error. If any missing input or changed SHA causes HOLD, report the fixed failure code.

Expected marker only after real owner-local run:

`R52_FULL_SOURCE_21_21_REVIEW_RECEIPTS_RECONCILED__GRAPH_HOLD`

The tool rechecks source ZIP SHA256, seven full story export root-message digests and original frozen 104 pins, 21 edge coverage, priority three complete-source decision identities/citations, all 18 decisions and their formal owner receipts, the 46 first-pass/16 quality hold cohort identities, and preservation of all no-admission states. Receipt mismatch or missing both-sided citations rejects the operation.

Outputs (0600, under a new 0700 directory, never overwritten):

- `R52_PRIVATE_21_WORLD_GRAPH_EVIDENCE_EDGES.jsonl` — one immutable provenance-indexed evidence row per pair, including citations and still-open semantic questions. **Private; do not commit.**
- `R52_PRIVATE_07_WORLD_GRAPH_OWNER_SIGNOFF_QUEUE.jsonl` — seven story-level units with all component/isolation, Gold87/v0.1, and content/safety signoffs left **pending**. **Private; do not commit.**
- `R52_ALL_21_WORLD_GRAPH_SAFE_AGGREGATE.json` — counts, pinned input decision digests, zero Train/Val, zero signed worlds; suitable for count-only progress archival.

This aggregated evidence is **not** sufficient to sign the seven components. Lack of a source-observed named link in two different export transcripts cannot rule out unrecovered aliases, author-shared canon, earlier tested exposure, transformed events, unexported target-time cards, or data reuse. A source-signed world-component map must explicitly resolve these before an admissible Train/Validation split proposal.

## Next qualification gates, in order

1. Review the seven story-owner queue against the *complete* seven original histories and any actual shared setting/alias declarations, plus historic Gold87 and v0.1 exposure. Convert discovered connected story worlds into conservative indivisible graph components. Do not unseal R50 answers merely for this stage.
2. Separately complete a final quality/safety owner disposition for each of the 46 first-pass-possible no-card training targets. Earlier R52 quality routing is first-pass evidence only.
3. Freeze a new experimental generic no-card prompt/task identity; run actual Qwen tokenizer/collator max-length and last-target-only mask checks; then propose component-disjoint Train/Validation allocation and evaluate per-world effective sample/token budgets.
4. Require explicit, separately reviewed immutable admission manifest and spend/run authorization before GPU training. Original Gold195 is unchanged.

CI synthetic checks: [R52 All 21 World Graph Ledger](https://github.com/sunxu/storyforge/actions/runs/39404984146). These checks use **fake story records** and do not replace the Mac run against original user-private sources.

**Always Train 0 / Validation 0 / No GPU / R50 sealed.**
