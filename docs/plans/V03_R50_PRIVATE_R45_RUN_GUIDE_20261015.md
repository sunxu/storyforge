# R50 — Private R45 49/15 source-isolation execution guide

**Scope:** StoryForge prospective test-only source stories 16–20. **Status:** scripted / real private gate still PENDING.

The no-GPU [source integrity workflow](https://github.com/sunxu/storyforge/actions/runs/38694118322) completed SUCCESS with 27 synthetic tests. It verifies 35 source files and runs exhaustive (step=1) normalized 120-codepoint comparisons against Git-tracked Gold195 and exposed old Test20. No matches were found under this exact-window criterion.

The R45 49/15 original input files are private and **not in the Git checkout**. The real R45 gate has NOT been executed, despite its five synthetic tests passing. Use the original frozen **uncompiled** Train49 and Val15 JSONL files; do not use alternative derived ms-swift input or screenshots.

```bash
cd ~/workspace/storyforge
git fetch origin audit/r49-r50-source-intake-20261015
git switch audit/r49-r50-source-intake-20261015
git pull --ff-only origin audit/r49-r50-source-intake-20261015

# Set these to your already-preserved, byte-exact R45 ORIGINAL train/validation JSONL:
R45_TRAIN=/absolute/private/path/train.jsonl
R45_VAL=/absolute/private/path/validation.jsonl
mkdir -p "$HOME/.local/share/storyforge/r50/private"
chmod 700 "$HOME/.local/share/storyforge/r50/private"

# Read-only input processing, NO remote calls/GPU; refuses overwrites and in-repo output.
python3 scripts/v03_r50_private_r45_isolation.py \
  --repo . \
  --train "$R45_TRAIN" \
  --validation "$R45_VAL" \
  --output "$HOME/.local/share/storyforge/r50/private/R50_R45_PRIVATE_ISOLATION.json"
```

Input integrity is pinned to historic R45 original Train49 SHA256 `e7442993088617c4eaefd3a0c9efc7651932f7048f34586046bf6d5b5981a742` and Val15 SHA256 `5ebbb3c6986a5ac4d294175bab1980ee61df08536f9b8438c8a67010630f1963`. Any mismatch, source-ID collision or 120-character all-offset fingerprint match is a **HOLD**. No report is written on failure.

A successful private result should have status `R45_FROZEN_49_15_EXACT_SCREEN_PASS__SEMANTIC_REVIEW_PENDING`; it still does not establish full semantic independence or authorize final Held-out use. The report contains only counts; source UUIDs, story text, message hashes and target answers are never printed or committed. Even if the report is reviewed, preserve original input paths and contents outside Git and keep any private report outside Git. The user may share the short final status and aggregate result, not raw story text.

## Remaining gates

1. Obtain the already-frozen R45 original 49/15 inputs and run the above no-GPU exact source checks.
2. Manually audit hidden character aliases, paraphrased scenes, cross-story relations and point-in-time card revisions in sources 16–20.
3. Have an independently uninvolved author prepare 40–60 prompt-only cases from >=4 truly separate worlds, with no reference assistant answers.
4. Freeze all content, SHA256, System/role cards, model generation parameters and independent six-dimension/hard-error rubric before any inference.
5. No GPU, data admission or model release until owner explicitly approves the specific further gate.

**Marker:** `R50_PRIVATE_R45_RUNNABLE_NOT_YET_EXECUTED__NO_GPU__NO_MODEL_PROMOTION`.
