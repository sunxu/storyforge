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


## Implementation (2026-10-08)
- `scripts/hf_evaluation_runner.py`: validation-only paired base/adapter inference,
  isolated Job ID directory, no SFT training and no held-out test access.
- `scripts/hf_submit_evaluation.sh`: default `sync`, paid `submit` requires
  `STORYFORGE_ALLOW_PAID_GPU=YES`.
- `scripts/prepare_eval_pairs.py`: checks result counts and nonempty responses,
  writes randomized A/B grading records and a separately stored, restricted
  `PRIVATE-answer-key.json`.

### CPU preparation & upload
```bash
pytest -q tests/test_prepare_blind_eval.py tests/test_prepare_eval_pairs.py tests/test_hf_evaluation_runner.py
bash scripts/hf_submit_evaluation.sh
```
The script expects the validation files generated in `/tmp` by the preceding
Gold-free CPU preparation instructions. The upload step is not GPU billable.

### Remaining launch gates
- The base-only `swift infer` CLI flags, including `--val_dataset_sample -1`,
  must be checked on CPU; the earlier inference smoke only verified adapter
  inference of a single prompt.
- Validate the output order and one-output-per-input behavior of ms-swift;
  the current pairer assumes output order matches prompt order.
- Freeze generation arguments (including deterministic decoding/seed) after
  compatibility checks. Merely matching command flags does not prove identical
  effective generation defaults.
- Confirm the `checkpoint-9` from the accepted Baseline still exists in Bucket.
- Review cost before paid GPU submission.

**Do not submit the GPU evaluation until these gates have been verified.**


## 2026-10-08 alignment hardening
- Paired output verifier now **fails closed** unless each result includes the
  matching original `messages` prefix. A shuffled, missing, or transformed
  prompt is refused instead of silently scored against the wrong story.
- Evaluation commands explicitly set `--seed 42`, `--data_seed 42` and
  `--val_dataset_shuffle false` for both arms.
- **Pending runtime compatibility**: it is not yet established that ms-swift
  4.5.3 writes original prompt `messages` in result JSONL. If absent, the
  evaluation correctly blocks instead of guessing, and the adapter/parser will
  need to be updated against a redacted real output sample.
- The base-only invocation, `-1` sample selector, and effective decoding
  strategy still require verification. Do **not** authorize GPU evaluation
  solely from a green Python unit-test run.


## Phase 3 validation blind review (GPU inference accepted)

HF Job `6ac776d5e7a0dae8a278755d` reported `PASS`, `pairs: 15`,
`paired_inference: PASS`, with `EVAL_GENERATION_PASS`. This establishes
generation and alignment, **not** model superiority.

### CPU-only reviewer workflow

Keep the private answer key separate and **do not disclose it to graders**.

```bash
# After downloading blind-pairs.jsonl privately from the accepted evaluation Job:
python scripts/analyze_blind_eval.py \
  --pairs /tmp/storyforge-validation-blind.jsonl \
  --scorecard /tmp/storyforge-validation-scorecard.csv \
  --results /tmp/storyforge-validation-inspection.json
```

Review the inspection report first. `possible_truncation` is a punctuation
heuristic, not a reliable count of truncated token-limit outputs. To
distinguish actual truncation, inspect generation metadata or a trusted
per-response generated-token count against the configured 128-token cap.

Fill every 1–5 rubric score and one `A`/`B`/`TIE` preference per row
while blinded. **Only after rating is complete**, download the private key
to a separate reviewer-controlled path and run:

```bash
python scripts/analyze_blind_eval.py \
  --pairs /tmp/storyforge-validation-blind.jsonl \
  --scorecard /tmp/storyforge-validation-scorecard.csv \
  --private-key /secure/PRIVATE-answer-key.json
```

Do not commit raw stories, scorer files, or private mappings to public Git.


## 2026-10-08: 128-token truncation diagnosis and 512-token validation rerun

The accepted 15-pair generation used `max_new_tokens=128`. A subsequent
CPU tokenizer audit found that **all 30 responses re-tokenize to exactly
132 tokens**. Together with the reported incomplete sentence endings, this
strongly indicates the generation cap was binding. Retokenized lengths are
*not* authoritative generated token counts, so do not claim that generation
termination reasons were proven.

The validation evaluation Runner now requests `max_new_tokens=512`; the
128-token output remains an engineering/alignment artifact but should **not**
be used as a final narrative-quality benchmark. The next evaluation needs
its own fresh HF Job ID and must never overwrite the accepted 128-token run.
Perform CPU-only checks first, then explicitly authorize any new A100 job.
Repeat the tokenizer audit on the 512-token outputs prior to blind scoring.
The 20 held-out test examples remain untouched.


## 2026-10-08: Gold-informed 1536-token full Validation evaluation

Gold-only tokenizer audit of Dataset v0.3 reports 100 Gold targets: mean
572.23, P95 969.9, max 1178 tokens; Validation max 1044 and 9/15 targets
exceed 512 tokens. The accepted 512-token paired validation Job
`6ac783ede7a0dae8a2788163` passed alignment, but 8/15 responses on
each arm re-tokenized close to the 512-token limit. That result remains
inadequate for final narrative-quality judgments.

The Evaluation Runner is now pinned at `max_new_tokens=1536` for **all
15 Validation samples in both arms**. No smaller pilot/qualification run is
required by this protocol. The full rerun is an explicitly authorized paid
GPU job and writes to a fresh job-specific directory. Do not reuse or
overwrite prior 128/512-token outputs. Keep identical Gold-free prompts,
model/adapter identities and decoding controls. Review completion and
actual stopping behavior before rating; Gold length alone cannot guarantee
natural model termination. The 20 held-out Test prompts stay locked.


## Context-enriched Chinese blind review (three independent reviewers)

Use the **exact Gold-free Validation prompt file** from the accepted paired
evaluation and its matching manifest. The exporter cryptographically verifies
all 15 prompt/pair IDs and hashes. It never reads Gold or the private answer key.

```bash
BUCKET="hf://buckets/adradar/storyforge-training"
hf buckets cp "$BUCKET/evaluation/v0.1/validation-prompts.jsonl" /tmp/storyforge-eval-prompts.jsonl
hf buckets cp "$BUCKET/evaluation/v0.1/validation-manifest.json" /tmp/storyforge-eval-manifest.json
hf buckets cp "$BUCKET/evaluation-runs/validation/6ac794fae7a0dae8a2788ee6/blind-pairs.jsonl" /tmp/storyforge-blind-1536.jsonl

python scripts/export_context_blind_review.py \
  --prompts /tmp/storyforge-eval-prompts.jsonl \
  --manifest /tmp/storyforge-eval-manifest.json \
  --pairs /tmp/storyforge-blind-1536.jsonl \
  --out-dir /tmp/storyforge-review-1536
```

The exporter creates `StoryForge_Reviewer_01.csv`,
`StoryForge_Reviewer_02.csv` and `StoryForge_Reviewer_03.csv`.
Each sheet includes system/story rules, past conversation, current user input,
and anonymous response A/B, followed by Chinese rating columns. Do not share
the confidential A/B key with reviewers. The source inputs may include private
story material and should not be committed to GitHub.
