# StoryForge v0.2 — R48 four-option blind review frozen before unblinding

**Record created:** 2026-10-14. **Decision:** `R48_THREE_SCORING_FILES_20_80_ORIGINAL_GOLD_SOURCE_FROZEN_PRE_UNBLIND`. No model identity has been read in this freeze, and no four-way quality winner is yet declared.

## Verified evidence

Owner committed three completed review CSVs on private GitHub `main` in immutable commit [`c4688f7`](https://github.com/sunxu/storyforge/commit/c4688f709352642cedec4e273c6c4be75279e786). The original source narratives and all four responses are present in these *owner-committed* CSVs. The review freeze does not add any extra story reply files to Git.

An independently run CI guard [R48 workflow 38576709308](https://github.com/sunxu/storyforge/actions/runs/38576709308) opened the actual committed R48 CSVs and compared **all 20 input contexts and all four candidate replies** against:
- The frozen R47 source CSV (three previously accepted anonymous model outputs per prompt).
- The canonical compiled v0.1 Test `data/compiled/v0.3/test.jsonl` (source Gold as the final Assistant reply; known SHA256 `d8eee6db5882d85dce7ffc01256e7c5b9b46e133bdb2cf8591259112b92e980d`).
- The v0.1 original prompt manifest (stable 20 sample IDs).

All 20×4 expected response multisets matched; the same four response texts and story context were identical in the three completed sheets. **No mismatch.** Header, preference, written rationale, severe-problem notes and **1,440 1–5 rating cells** were valid. All 60 individual reviewer-case written rationale fields contained at least one quote found in the material, although exhaustive semantic correctness of every quoted claim remains a separate review concern.

### Frozen exact bytes

| Completed CSV | Git blob SHA1 | SHA256 from successful CI |
|---|---|---|
| `R48_Reviewer_01_completed.csv` | `d5e4c259ea0a69904c7dbfe21abac67e4e935514` | `48ba53e37a5d9dfa536cbcfac2e189feac617e06eb1a79978fbc66dbeb994cfb` |
| `R48_Reviewer_02_completed.csv` | `deecd293903ca89ba406addc9a4cbf9956fae8b0` | `4ac13669fb92b969fb7f30cac037aaec418cd7963762240ad5c34aab3a44aab7` |
| `R48_Reviewer_03_completed.csv` | `0185b3cf041f861384cf3cb0bbafb773ed896e87` | `41cf53daedcb3db9dfeea510507b44413cd5399adda8d61361c196a1ab282ee4` |

### Anonymous statistics (NOT model results)

- Reviewer 01 anonymous preferences: A=6, B=5, C=5, D=4.
- Reviewer 02: A=7, B=2, C=6, D=5.
- Reviewer 03: A=6, B=4, C=5, D=5.
- **60 individual votes:** A=19, B=11, C=16, D=14.
- **20 case majorities:** A=6, B=3, C=5, D=6.
- **12 cases unanimous**; **8 cases split 2:1**, none without majority.
- Models are randomized differently per item. **Do not apply these letter totals to Gold, Base, v0.1 or v0.2 as whole-model scores.** Only the separately held private key can correctly identify each response.

## Remaining independent check and coordinator-only unblinding

Although the original content has been *directly* reconciled against canonical Gold + frozen R47 outputs, the CI cannot access the original unscored R48 CSVs kept in the owner's local `reviewers/` directory. Compare those files before opening the key:

```bash
cd ~/workspace/storyforge
git pull --ff-only origin main
bash scripts/v02_r48_unblind_git.sh check
```

Expected terminal markers:

```text
R48_THREE_SCORING_FILES_20_80_ORIGINAL_GOLD_SOURCE_FROZEN_PRE_UNBLIND
R48_THREE_REVIEWERS_20_CASES_1440_RATINGS_COMPLETE_KEY_NOT_READ
R48_PREUNBLIND_SOURCE_AND_RATINGS_PASS_NO_KEY_READ
```

Once they PASS, coordinator can permit unblinding **without another GPU run**:

```bash
STORYFORGE_R48_OWNER_UNBLIND=YES bash scripts/v02_r48_unblind_git.sh unblind
```

This recreates and archives the freeze evidence locally and writes a private result:

```text
~/.local/share/storyforge/r48/r48-20261014-gold-four-arm-20/coordinator/R48_PRIVATE_UNBLIND_DIAGNOSTIC.json
```

On success: `R48_GOLD_FOUR_ARM_RETROSPECTIVE_UNBLIND_NOT_PROMOTED`.

**Privacy:** This private result may be shared selectively with the coordinator for aggregate analysis; do not commit the key to ordinary Git. Full R48 scored review CSVs already exist in the private repository with owner approval. No ZIP or LFS objects created for this stage.

## Scientific limitations

This uses the **already exposed v0.1 Test 20**, not fresh independent Held-out. The Gold source reply can have its own violations and is **not** a perfect ground truth or the fourth model. Original v0.1 Test includes rich cards, whereas R46 fine-tune used generic no-card prompts. This diagnostic does **not** authorize v0.2 model quality promotion or more GPU training.

The CSV files and evidence do not independently establish distinct review authorship; review judgments remain claims of separate evaluation rather than a verified three-person study.
