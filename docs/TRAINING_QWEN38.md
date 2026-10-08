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
pip install -U ms-swift
pip install -U "transformers>=5.2.0" qwen_vl_utils decord
pip install -U bitsandbytes
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

Only after smoke acceptance:

```bash
CUDA_VISIBLE_DEVICES=0 \
swift sft configs/qwen38-27b-qlora-v0.1.yaml
```

The baseline is intentionally conservative. With only 65 training samples, training quality must be judged by held-out narrative evaluation, not by minimizing train loss.
