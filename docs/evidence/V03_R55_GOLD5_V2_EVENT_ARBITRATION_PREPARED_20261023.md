# StoryForge R55 Gold5 v2 — Private independent event adjudication preparation

Date: 2026-10-23 (Asia/Singapore). **Status: code and synthetic tests ready, no real case adjudication or promotion performed.**

## Evidence-backed candidate decision

- Existing Owner-reported 3-round unblind: Pair v0.3-A vs v0.2 = 10:10 case majority, 30:30 reviewer votes; mean six-axis 3.216667 vs 3.363889 respectively (v0.3-A lower in all axes). In separate Four model-only v0.2 has highest overall mean 3.486111; in Five Gold+four model v0.2 is highest scoring model 3.461111, Gold reference 3.500000. See `docs/evidence/V03_R55_GOLD5_V2_OWNER_UNBLIND_DECISION_20261023.md`.
- 20 old, historically exposed development cases from 2 story worlds: not new independent Held-out. R54 checkpoint-16 remains `NO_GO_FOR_PROTECTED_R50_NOW` and `NOT_PROMOTED`. Existing R50 candidate cases remain protected; no inference or retraining authorized.
- Source aggregation includes **unadjudicated Reviewer×case×arm** player-agency and forbidden/hard-fact marks. They are not confirmed events. It is technically unsound to sum flags over Pair/Four/Five as distinct failures: the same candidate replies recur.

## New private event adjudication preparation

Prepared `StoryForge_R55_GOLD5_EVENT_ARBITRATION_NOJOB_20261023.patch`, SHA256 `6bc6e7cf5aa874e09cef586bc9ce9baa072466c7fbe4fd03589a761c8b14f236` and corresponding ZIP SHA256 `55150955f0aefb38fe555a43bad2ecc7e0ec2289e8c4fd9ce3992aeaf6eebcbe`.

Patch adds only source code/test/guide:

- `scripts/v03_r55_gold5_event_arbitration.py`
- `tests/test_v03_r55_gold5_event_arbitration.py`
- `docs/R55_GOLD5_EVENT_ARBITRATION_OWNER_CN.md`

Implementation intentionally reuses the existing locally installed original owner-unblind and review-freeze modules; it revalidates the full nine scored CSVs, three frozen receipts, SHA256 and coordinator key against Owner-reported pins, without accessing R50. It checks across-round original story-rule/history/current-user field equality. It merges a repeated Reviewer flag only to **(same original question, same original candidate reply)** into a provisional arbitration *subject*; it never claims this deduplicates semantic events. New random opaque candidate tokens, source text, and frozen prompt context appear in reviewer-only **private** packets, without model arm names or historic reviewer scores. Full source IDs, arm mappings, reviewer-evidence quotations and SHA256s are kept separately in an Owner-only coordinator index.

Two preparation scopes:

- `--scope flagged` (default): only candidate replies marked by ≥1 Reviewer in any of Pair/Four/Five, with each packet asking the arbitrator to assess **both** agency and hard-rule categories. This is a *selected* set; event counts here must **not** be interpreted as unbiased prevalence or generalization. Per-round Reviewer observations remain frozen and linked only in the private Owner index. Case-level group count is only known after running the tool on actual private inputs.
- `--scope all`: 20×5=100 candidate replies, includes unflagged negative controls. It still represents 20 distinct historical prompts and could require significant review effort.

An independently blinded adjudicator fills an exact-response-quote/visible-context-quote and a grounded rationale for each `CONFIRMED` finding, or gives `REJECTED` / `HOLD_INSUFFICIENT_EVIDENCE` with reason; Original Gold receives the same review standards. The `validate` step fail-closes on missing decisions, changed packet bytes, forged quotations, missing rationale, duplicate candidate tokens and unsupported content. This validates form and **quotation existence**, not semantic correctness, reviewer identity or independence. The actual private arbitrator output must be reviewed before any model error-rate estimate.

## Local synthetic checks and privacy

Patch `git apply --check` and `git apply` succeeded in an independent synthetic repo containing prior scripts. **35/35 unittest checks PASS** (18 dedicated new tests plus 17 imported original unblind regression tests). ZIP CRC and SHA256 of packaged sources verified. These were synthetic only; actual nine private review CSVs and private mapping were not loaded in this environment. Source scripts have not been individually committed to GitHub in this action; use the patch on Owner Mac. No private stories, case IDs, Gold targets, mappings or reviewer textual evidence committed.

## Owner next step

Apply the patch in `sunxu/storyforge`, run `python3 -m unittest discover -s tests -p 'test_v03_r55_gold5_event_arbitration.py' -v`, then locally run:

```bash
ROOT="$HOME/.local/share/storyforge/r55/gold5-dev20"
python3 scripts/v03_r55_gold5_event_arbitration.py --mode prepare \
  --pack "$ROOT/owner-pack-v2" \
  --pair-dir "$ROOT/frozen/pair-v1" \
  --four-dir "$ROOT/frozen/four-v1" \
  --five-dir "$ROOT/frozen/five-v1" \
  --scope flagged --out-dir "$ROOT/event-arbitration-v1"
cat "$ROOT/event-arbitration-v1/safe/R55_GOLD5_ARBITRATION_PREP_SAFE_COUNT_ONLY.json"
```

Only safe counts should be returned to the assistant. Send the blinded source packet and blank decision template to a **new separate adjudicator**, not the coordinator source identity index. If using a remote AI reviewer, Owner must choose to disclose private story content to that service. No model promotion follows automatically.

Current status: `R55_GOLD5_EVENT_ARBITRATION_CODE_SYNTHETIC_PASS__REAL_OWNER_PREP_PENDING__R54_NO_GO_R50_NOW__NO_GPU`.
