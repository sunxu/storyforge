# Qwen3.8-27B training gate

## Accepted dataset

Dataset v0.3 is the first training-eligible StoryForge dataset.

Token budget with the Qwen3.8 tokenizer:

- samples: 100
- train / validation / test: 65 / 15 / 20
- P50 total tokens: 6,510
- P90: 15,282
- P95: 15,816
- P99: 16,162
- max: 16,259
- <= 16,384: 100%

The held-out test set must never be passed to `swift sft`.

## Gate

Before a real run:

1. Run `configs/qwen38-27b-qlora-smoke.yaml`.
2. Confirm no CUDA OOM.
3. Confirm training loss is finite.
4. Confirm validation executes.
5. Confirm a LoRA checkpoint is saved.
6. Reload the adapter and run at least one inference prompt.
7. Record peak GPU memory and wall-clock step time.

Only after those checks should `configs/qwen38-27b-qlora-v0.1.yaml` be used or tuned.

## Environment

Current ms-swift model support for Qwen3.8-27B requires a recent transformers release.
Use a fresh Linux GPU environment rather than the tokenizer-only local environment.

Suggested installation:

```bash
python3 -m venv .venv-train
source .venv-train/bin/activate

pip install -U pip
pip install -U "ms-swift==4.5.3" "transformers==5.16.1" \
  "qwen-vl-utils>=0.0.14" "bitsandbytes==0.50.2"
```

Optional after the baseline is stable:

```bash
pip install -U flash-attn --no-build-isolation
pip install -U liger-kernel
```

Do not add DeepSpeed to the initial single-GPU QLoRA smoke test.

## Label-mask policy

StoryForge is target-only SFT: only the final Gold assistant response is supervised.

Both smoke and baseline configs use:

```yaml
loss_scale: last_round
disable_ignore_empty_think: true
add_non_thinking_prefix: false
```

ms-swift 4.5.3 automatically appends `ignore_empty_think` for Qwen hybrid thinking
templates. The explicit flags above preserve the exact audited `last_round` strategy
and prevent a synthetic empty thinking prefix from becoming part of the Gold response.
The audit verifies that the template has preserved the original final Gold content.

ms-swift's SFT default strategy supervises all assistant responses, including history, so it is
not appropriate for these compiled multi-turn samples.

Label audits must allow template-owned response suffix/control tokens attached to the final
assistant response while rejecting any supervised system, user, or historical assistant tokens.

The HF Job runner audits every train and validation sample before invoking `swift sft`.
Its runtime guard checks the parsed arguments, actual template strategy, parameter dtypes,
and quantized `Linear4bit` weights with bfloat16 compute before the first training step.

## Smoke command

```bash
CUDA_VISIBLE_DEVICES=0 \
swift sft configs/qwen38-27b-qlora-smoke.yaml
```

## Baseline command

Only after smoke acceptance **and a separate baseline config/GPU-memory review**:

```bash
CUDA_VISIBLE_DEVICES=0 \
swift sft configs/qwen38-27b-qlora-v0.1.yaml
```

The baseline is intentionally conservative. With only 65 training samples, training quality must be judged by held-out narrative evaluation, not by minimizing train loss.


## 2026-10-08 Smoke closure

The accepted A100 80GB engineering smoke completed 3 steps, evaluation,
checkpoint save, adapter reload and inference. See
[`docs/evidence/GPU_SMOKE_20261008.md`](evidence/GPU_SMOKE_20261008.md).

The smoke used rank 32 and peak sampled GPU memory 61007 MiB. This does
**not** yet establish rank-64 baseline memory headroom, final quality,
training convergence or generalization.

## Baseline SFT readiness

Baseline candidate currently uses 65 train / 15 validation, rank 64,
gradient accumulation 8, 16,384 max length and one epoch. Effective
optimizer-step count is roughly nine for 65 examples at batch 1 with
accumulation 8; the training framework's final partial-step behavior
must be checked. The baseline candidate now explicitly sets step-based evaluation and saving
at every 3 optimizer steps (rather than 8), with logging each step.
This improves early visibility but still does not establish model quality or
prevent overfitting. Verify ms-swift 4.5.3 resolves these strategies and the
final incomplete accumulation step correctly in the CPU preflight.

Hold-out policy: do not feed the 20 test samples to the trainer,
validation, checkpoint selection or hyperparameter tuning.

Recommended next action: complete a CPU-only config sanity check and
plan a short rank-64 capacity qualification before launching the full epoch.

## Important execution safeguard

The accepted `scripts/hf_job_runner.py` is a **smoke-only runner**: it
hard-codes the smoke config and `--max_steps 3`. **Do not** use
`scripts/hf_submit_smoke.sh --submit` to start baseline training: it will
start another 3-step smoke, not a one-epoch job. A dedicated baseline runner
with unique run paths, explicit config identity, finite-loss/checkpoint
assertions and rank-64 GPU capacity gates must be built and tested first.

The current candidate config is not a claim that rank 64 fits A100 80GB.
A full epoch must not be launched until a bounded GPU capacity test succeeds.
