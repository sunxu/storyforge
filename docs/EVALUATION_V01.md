# StoryForge Phase 3 — Blind Model Quality Evaluation v0.1

**Status: PROTOCOL DRAFT; no GPU inference performed by this document.**

## Goal
Measure whether baseline QLoRA improves interactive-fiction continuations over
Qwen/Qwen3.8-27B base, not merely whether a checkpoint can load.

## Data isolation
1. Build prompts from **validation** split (15 samples) to calibrate the
   generation protocol and rubric. The prompt exporter drops final Gold and all
   training-only `loss` fields, and writes a hash manifest with no Gold.
2. Freeze decoding settings, prompt hashes, scoring sheet and review procedure.
3. Only then run the **story-isolated 20 held-out test examples**, once, for
   final comparison. Do not use them to select ranks, epochs, checkpoints,
   decoding parameters, or iterate based on outcomes.
4. All story and model outputs stay in the private HF Bucket or secured local
   storage, not in public GitHub.

## Gold-free CPU preparation
```bash
python scripts/prepare_sft.py \
  --source data/compiled/v0.3/validation.jsonl \
  --output /tmp/storyforge-validation-sft.jsonl
python scripts/prepare_blind_eval.py \
  --source /tmp/storyforge-validation-sft.jsonl \
  --output /tmp/storyforge-blind-validation.jsonl \
  --manifest /tmp/storyforge-blind-validation-manifest.json
```

Do not run a billable GPU evaluation until both model commands have been
independently CLI-checked. The earlier successful Adapter smoke inference
supports the tuned-model path but does not verify a new base-only comparison.

## Paired inference protocol
- Base and Adapter consume **identical** Gold-free prompts and context.
- Fix model revision, max input length, generation token cap, sampling
  parameters and generation seed; record all values.
- Use deterministic decoding where feasible; identical seeds alone do not
  guarantee identical generations from different model weights.
- Do not reveal model identity or Gold to graders; randomize and record
  mapping outside graders' view.
- Keep raw outputs and errors, including empty or truncated generations.

## Human scoring rubric (1–5 each)
- Narrative continuity: consistent with established events and setting
- Character consistency: stable goals, voice, relationships and facts
- User instruction adherence: follows latest user direction and constraints
- Writing quality: clarity, vividness, appropriate tone without repetitive filler
- Interactive progression: offers meaningful developments without hijacking agency

Primary outcome: paired blind preference (Base / Adapter / Tie), separately
from mean rubric scores. Track critical failures and uncertainty; with only 20
held-out prompts, avoid asserting statistically robust improvements.

## Acceptance rules
- Pipeline readiness: both models produce valid, nonempty outputs, all prompt
  hashes match, and no Gold target is in generation input.
- Model quality: not yet accepted until blind grading is completed and scores
  are reviewed. A successful train loss or eval loss is not sufficient.
