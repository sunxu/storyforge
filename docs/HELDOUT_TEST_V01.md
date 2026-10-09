# StoryForge v0.1 — Frozen held-out Test execution

**Status: READY FOR LOCAL PREPARATION; no test GPU Job launched by this document.**

Acceptance context: Baseline v0.1 checkpoint-9 was engineering-accepted;
Validation paired generation and blinded review completed and unblinded.
Validation does **not** establish generalization. This held-out evaluation
must not change model weights, dataset membership, hyperparameters, or the
previously frozen decoding recipe.

- Source: private compiled Dataset v0.3 `test.jsonl`, exactly 20 samples
- Input: final Gold assistant stripped with `prepare_sft.py` then
  `prepare_blind_eval.py`; no Gold target is sent to inference
- Models: original Qwen/Qwen3.8-27B and frozen Baseline checkpoint-9
- Inference: BF16, bitsandbytes 4-bit, `max_new_tokens=1536`,
  `temperature=0`, `seed=42`, `data_seed=42`, no shuffle
- Output: `evaluation-runs/test/<JOB_ID>/`
- No change to Validation run or private answer key

## CPU preparation (local Mac, no A100)

```bash
cd storyforge
git pull --ff-only
pytest -q tests/test_hf_test_evaluation_runner.py
python scripts/prepare_sft.py \
  --source data/compiled/v0.3/test.jsonl \
  --output /tmp/storyforge-test-sft.jsonl
python scripts/prepare_blind_eval.py \
  --source /tmp/storyforge-test-sft.jsonl \
  --output /tmp/storyforge-test-prompts.jsonl \
  --manifest /tmp/storyforge-test-manifest.json \
  --allow-heldout
bash scripts/hf_submit_test_evaluation.sh
```

The preparation commands refuse existing output files. Check or remove only
your own stale local `/tmp/storyforge-test-*` files before retrying; never
overwrite prior completed test results without an explicit audit trail.

## Paid full evaluation, only after CPU and CI PASS

```bash
STORYFORGE_ALLOW_PAID_GPU=YES bash scripts/hf_submit_test_evaluation.sh submit
```

This runs **all 20 held-out prompts on both arms**. It creates a new paid
A100 Job and stops at a 240-minute timeout. Do not submit repeatedly if the
job is merely slow. Check `summary.md` and `EVAL_GENERATION_PASS` inside
the resulting `evaluation-runs/test/<JOB_ID>` before rating.

## Blind rating

Use `export_context_blind_review.py` with the new test prompts,
manifest and test `blind-pairs.jsonl`. It exports three identical blinded
CSV reviewer files. The private answer key stays restricted, and graders
must never see it before submitting ratings. Follow the same five-dimension
rubric, preference and arbitration approach from Validation.

**Do not use these test scores to tune this v0.1 checkpoint and then call
a subsequent retest of the same 20 prompts independent.** Preserve test
outputs and report uncertainty explicitly.
