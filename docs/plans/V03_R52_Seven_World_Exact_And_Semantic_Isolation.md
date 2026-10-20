# R52 — Gold108 46-case historical UUID and world-component preflight

**2026-10-20 | read-only inputs | no Train/Val | no sealed-R50 access | no GPU**

The owner provided an authenticated local post-quality closure output: **62/62** frozen R52 quality judgments revalidated, **205** citations rechecked, **46** preliminarily feasible no-card samples and **16** target-quality Holds across **7 source story UUIDs**. These seven UUIDs **are not yet seven independent world components**.

## What prior evidence does and does not prove

- The pinned [v0.1 historic data overlap audit](../../evaluations/v0.2/admission-audit-20261013/v01_overlap_audit.json) found no exact UUID or same-target collision between Gold108 and the v0.1 Train/Validation/Test data sets. Earlier Gold87 had an actual prior v0.1 Train UUID overlap (21 old frozen candidates versus 2 previously trained examples), so do not merge it automatically.
- The R45 historical Train/Val world list and the known 04↔07 linked-story component are prior evidence, *not* evidence that all R52 seven stories are independent.
- Exact UUID comparison cannot discover different-UUID same-world aliases, same characters, linked narrative universes, semantic copies, or R50 heldout intersection. The script intentionally **does not open the sealed R50 set**.
- User's content ownership attestation has been recorded for StoryForge. Target-specific quality/safety signoff, exact new no-card experimental input and world isolation are still independent release gates.

## Run new exact UUID preflight locally

The script is `scripts/v03_r52_world_exact_isolation.py`. On the Mac's StoryForge audit branch:

```bash
cd ~/workspace/storyforge
git pull --ff-only

d="$HOME/.local/share/storyforge"
install -d -m 700 "$d/r52/world_isolation"

python3 scripts/v03_r52_world_exact_isolation.py \
  --repo . \
  --r52-post-quality-dir "$d/r52/post_quality" \
  --out-dir "$d/r52/world_isolation"
```

Expected result **only if old v0.1 file SHA256 pins and all 7 source UUIDs match the prior disjointness evidence**:
`R52_V01_EXACT_UUID_SCREEN_PASS__WORLD_GRAPH_AND_SEALED_TEST_HOLD`.

It validates the 46-shortlist and 16-HOLD records, frozen 7-source-story inventory, full v0.1 data/compiled/v0.3 Train 65/15 story groups, Validation 15/2, Test 20/2 and their historical SHA256 digests; compares all seven R52 story IDs with these exact historical split UUIDs. Any overlap or hash mismatch emits a fixed HOLD and exits without writing a success receipt.

The stdout includes **only safe counts and hashes**, and all stored files remain owner-private: `0700` output directory and `0600` files.

Outputs:

- `R52_WORLD_EXACT_ISOLATION_SAFE_AGGREGATE.json`: safe SHA256 pins, v0.1 exact UUID match counts, unresolved gates.
- `R52_PRIVATE_07_WORLD_COMPONENT_REVIEW_QUEUE.jsonl`: seven per-story review records with as-yet blank linked-world/manual evidence and **no assigned Train/Val split**.

Do **not** mark `owner_component_isolation_signed=true` based solely on UUID results. Reviewer/owner must reconcile character IDs, meaningful aliases, named locations, linked world/story pairs including 04↔07, and any historical trained/test exposure. Do not label sealed R50 case membership checked: this program intentionally never reads it.

## Subsequent admissibility work

Once the exact screen runs, obtain human-confirmed linked-world graph decisions on the seven private story records, evaluate the 46 quality-possible cases for final player agency, participant ages, consent/content safety, and narrative quality, then decide component-level Train vs Validation. The exact generic no-card prompt bytes/sha and source-visible history rendering must be frozen before the pinned tokenizer and actual last-target-only `ms-swift` labels gate. **None of these can be assumed from reviewer quality routing alone.**

This checkpoint remains **Train 0 / Validation 0 / no GPU**. The CI workflow `R52 Seven-world UUID Preflight (synthetic only)` exercises disjoint, tampered graph and collision HOLD scenarios with fake files only; real private screening must run on the owner's Mac.


## Owner-local exact UUID screen PASS and bounded 21-pair handoff (2026-10-20)

Owner reported `R52_V01_EXACT_UUID_SCREEN_PASS__WORLD_GRAPH_AND_SEALED_TEST_HOLD` after verifying all pinned historical v0.1 split SHA256 bytes, 46 positive and 16 held R52 candidates, and **zero** exact R52 story-UUID intersection with v0.1 Train/Validation/Test. This establishes the identity screen only; **7 source stories remain 7 unverified linked-world components**.

Next private tool `scripts/v03_r52_world_semantic_review_kit.py` prepares **7 source dossiers and 21 story pair tasks**, each with exact frozen R51 target/source SHA and short bounded excerpts. See [task preparation and review guide](V03_R52_Seven_World_Semantic_Review_Kit.md). It intentionally reads no R50 sealed test. Synthetic CI for this tool passed, [run 39386164241](https://github.com/sunxu/storyforge/actions/runs/39386164241). A bounded no-match result cannot certify complete semantic isolation; the owner must subsequently review original full-story aliases, Gold87, historical v0.1 exposure and linked-world edges before any Train/Val signing.

**All original training admission remains `PENDING_NOT_APPROVED`; Train 0 / Validation 0 / no GPU.**
