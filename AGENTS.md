# AGENTS.md

## Project

StoryForge is the training and evaluation pipeline for interactive narrative language models.

Current target:

- Base model: `Qwen/Qwen3.8-27B`
- Training method: QLoRA / SFT with ms-swift
- Accepted dataset: `data/compiled/v0.3`
- Token budget: `max_length=16384`
- Dataset split: 65 train / 15 validation / 20 held-out test
- Held-out test data MUST NOT be passed to training or validation.

Read these files before making training changes:

- `README.md`
- `docs/DATASET_V0_1.md`
- `docs/TRAINING_QWEN38.md`
- `configs/qwen38-27b-qlora-smoke.yaml`
- `configs/qwen38-27b-qlora-v0.1.yaml`

## Codex operating rules

### 1. Preserve dataset integrity

Do not modify raw or compiled datasets unless the task explicitly requires it.

Never commit:

- `data/raw/`
- `data/private/`
- `data/compiled/`
- model weights
- LoRA adapters
- checkpoints
- secrets
- SSH private keys
- Hugging Face tokens

These are intentionally excluded by `.gitignore`.

The held-out test set is for final evaluation only.

Do not use:

`data/compiled/v0.3/test.jsonl`

for:

- training
- validation
- hyperparameter selection
- checkpoint selection
- prompt tuning

### 2. Remote GPU safety

Remote GPU work must be auditable and reversible.

Before installing or training, collect:

```bash
hostname
uname -a
nvidia-smi
python3 --version
df -h
free -h
```

Do not:

- destroy or reformat disks
- alter firewall rules
- modify unrelated system services
- expose new public ports
- install secrets into the repository
- run destructive cleanup outside the StoryForge workspace
- terminate unrelated GPU processes without explicit approval

Prefer a project-local Python virtual environment.

Do not use `sudo` unless it is strictly required and explicitly authorized.

### 2.1 Hugging Face-only token preflight (mandatory)

**All StoryForge model-tokenizer preflights MUST run in a Hugging Face environment, not on the user's Mac.** This includes token counts/length distribution, context-window checks, chat-template rendering, tokenizer/model-revision compatibility, and R58 Gold195 A/B blind-review prompt token-budget checks.

- Prefer **Hugging Face CPU Jobs** for token-only preflights; use an HF Sandbox or other HF-hosted CPU runtime only when appropriate and authorized. A GPU is not required solely to tokenize or count tokens.
- The Mac is for preparing, validating file integrity, securely staging/syncing private inputs, and retrieving SAFE receipts/results. **Do not instruct the user to install Transformers, download model tokenizers, or execute model-specific token preflights on the Mac.**
- Pin the **exact model ID and immutable revision** and the relevant tokenizer/chat-template version; match the eventual inference or SFT runtime to avoid a misleading preflight.
- Use HF-private storage/mounts for source text, world cards, blind-review packets, and derived prompts. Do not upload private content or Owner crosswalks to GitHub, expose them in Job logs or chat, or give reviewer A access to reviewer B's data.
- Produce only SAFE aggregate receipts outside private storage (PASS/HOLD, counts, maximum token length, model/revision identifiers as appropriate). Never silently truncate history, rewrite the frozen Gold, or treat a preflight PASS as literary quality approval or training admission.
- **Paid HF CPU execution needs the applicable cost authorization.** Never infer that approval for a CPU preflight authorizes a GPU Job; GPU inference/training requires separate explicit approval.

For R58 Gold195 literary pilot13, perform A/B tokenizer checks on HF CPU against each reviewer's staged PRIVATE input and the same pinned model revision, chat template, and context budget planned for the corresponding GPU reviewer. Fail closed on a mismatch or over-budget prompt, and do not launch the GPU automatically.

### 2.2 Reuse existing HF token-preflight tooling (mandatory)

**Never write a new one-off token-budget/tokenizer preflight for each StoryForge round.** Inventory and reuse existing code, tested HF CPU execution wrappers and SAFE receipts before creating a new script:

- scripts/hf_cpu_preflight.py: SFT dataset, label flags, and training-config checks; **not** a real model-tokenizer length audit.
- scripts/v03_r50_hf_cpu46_audit.py and R53 CPU40 worker: earlier HF CPU staging, source/version verification and result-recovery patterns.
- experiments/r58_quality/hf_cpu132.sh + gold195_hf_review_cpu_worker.py: existing sync/submit/verify and genuine input_ids token-length measurement for 132 cases.
- experiments/r58_quality/r58_hf_cpu_literary_token_preflight.py: 13-case A/B literary-judge input adapter; reuse its exact GPU judge-prompt serializer, do not fork this path again.
- Real ms-swift label-mask/data-collator checks are separate from generic tokenizer-only token counts; never substitute one for the other.

**Reuse an existing valid preflight receipt** when private input bytes, serialized prompt/template, model ID and immutable revision, tokenizer/runtime version, thinking flag, max context, reserved output tokens and audit semantics are identical. A new round name or relocated file does not justify a new paid CPU run. If a material input or parameter changes, invalidate the affected cached result and document the change; recompute only affected cases **when an independently verified per-case incremental cache exists**, otherwise recompute the validated batch. Do not claim that the current R58 all-13 batch adapter supports incremental case-level reuse.

Centralize actual input_ids extraction and length/distribution checks instead of copying them into each reviewer/worker. NEVER use len(BatchEncoding) as the token count: it returns the number of encoding fields and previously produced a false 2-token result. Reject missing, malformed, zero or implausibly small token sequences; test both list and BatchEncoding-like mapping returns. Always check prompt tokens plus reserved output tokens, without silently truncating history.

**Shared implementation now exists:** `src/storyforge_dataset/token_preflight.py` provides the single `input_ids`, `encode_chat`, token-length summary, and serialized-prompt identity implementation. HF staging copies the exact bytes as PRIVATE `token_core.py`. R58 pilot13 CPU/GPU adapters reuse it; new experiments must extend these components rather than clone the algorithms. See `docs/standards/HF_TOKEN_PREFLIGHT_REUSE_CN.md`. Keep historical frozen scripts/evidence unchanged. Reuse does not imply approval to run HF CPU or GPU; paid execution and GPU authorization remain separate. Mac performs safe staging and SAFE receipt verification only; tokenizer work runs on HF CPU.

### 3. Training gate

Training is strictly staged.

#### Stage A — Environment qualification

Verify:

- NVIDIA GPU visible
- CUDA runtime usable
- sufficient free VRAM
- sufficient disk space
- repository is clean or local changes are documented
- Qwen tokenizer/model can be resolved
- ms-swift CLI is available

Recommended environment:

```bash
python3 -m venv .venv-train
source .venv-train/bin/activate

pip install -U pip
pip install -U ms-swift
pip install -U "transformers>=5.2.0" qwen_vl_utils decord
pip install -U bitsandbytes
```

Do not add DeepSpeed to the initial single-GPU smoke test.

#### Stage B — Dataset qualification

Run:

```bash
storyforge-dataset validate \
  data/raw/100条作品回答范例_完整上下文_JSONL_20260930 \
  --expected-selected 100
```

Then verify `data/compiled/v0.3` exists.

Run the following token analysis **in Hugging Face CPU (not on the Mac)**, using the corresponding private mounted inputs and pinned tokenizer revision:

```bash
storyforge-dataset analyze \
  data/compiled/v0.3 \
  --model Qwen/Qwen3.8-27B
```

Acceptance:

- 100 samples
- <= 16384 tokens: 100%
- max <= 16384
- no analyzer errors

Do not rebuild v0.3 unless required.

#### Label-mask qualification

StoryForge SFT supervises only the final Gold assistant response.

The training configs MUST use:

```yaml
loss_scale: last_round
```

Do not use ms-swift SFT's default loss strategy for StoryForge multi-turn samples because
the default also supervises historical assistant responses.

When auditing labels, Qwen/ms-swift may supervise assistant response suffix/control tokens
(e.g. response terminators). These template-owned suffix tokens are not history/system leakage.

A label-mask audit must distinguish:

- forbidden: system tokens
- forbidden: user tokens
- forbidden: historical assistant response tokens
- allowed: final Gold assistant content
- allowed: template-owned suffix/control tokens attached to the final response

If an audit reports a small number of leaked tokens, decode their exact token IDs and positions
before changing the training mask. Never waive the audit without identifying them.

#### Stage C — Smoke training

Run only:

```bash
CUDA_VISIBLE_DEVICES=0 \
swift sft configs/qwen38-27b-qlora-smoke.yaml
```

Smoke acceptance requires all of:

- model loads successfully
- 4-bit quantization succeeds
- dataset parses successfully
- forward pass succeeds
- backward pass succeeds
- no CUDA OOM
- training loss is finite
- validation step succeeds
- LoRA checkpoint is saved
- adapter can be reloaded
- one inference sample succeeds

Record:

- GPU model
- peak VRAM
- step time
- total smoke wall time
- package versions
- output/checkpoint path
- any warnings

If smoke fails, STOP.

Do not start the baseline run after a failed smoke.

Fix only the minimum necessary issue and rerun smoke.

#### Stage D — Baseline training

Baseline training may start only after Stage C passes.

Command:

```bash
CUDA_VISIBLE_DEVICES=0 \
swift sft configs/qwen38-27b-qlora-v0.1.yaml
```

Before starting baseline training, re-check GPU memory and disk space.

Do not change hyperparameters merely to improve training loss.

With 65 training samples, overfitting risk is high.

### 4. Evidence

Create local evidence under:

```text
runs/<run-id>/
```

At minimum save:

```text
environment.txt
nvidia-smi-before.txt
pip-freeze.txt
command.txt
stdout.log
stderr.log
nvidia-smi-after.txt
summary.md
```

The `summary.md` must state:

- PASS / FAIL
- exact Git commit
- exact config file
- exact dataset path
- exact base model
- GPU type
- peak VRAM if available
- training steps completed
- final/observed loss
- checkpoint path
- unresolved warnings/issues

Do not commit large logs, model weights, datasets, or checkpoints unless specifically requested.

### 5. Source control

Before modifying source:

```bash
git status --short
git rev-parse HEAD
```

Keep changes scoped.

Run:

```bash
ruff check .
pytest -q
```

before committing code changes.

Do not rewrite history or force-push.

Do not modify `main` history destructively.

### 6. Decision rules

If the remote GPU has less memory than expected, do NOT silently reduce `max_length` or change the dataset.

Report the constraint first.

If `16K` smoke OOMs, acceptable next experiments are, in order:

1. enable/verify gradient checkpointing
2. verify batch size is 1
3. inspect quantization actually loaded in 4-bit
4. consider memory-efficient attention if compatible
5. only then propose a shorter max_length or length-bucket strategy

Do not change the accepted Dataset v0.3 content merely to make training fit.

### 7. Completion condition

The task is not complete merely because a training process started.

For smoke training, completion means the Stage C acceptance criteria are satisfied.

For baseline training, completion means:

- training exits successfully
- final adapter/checkpoint exists
- validation completed
- evidence summary is written
- no held-out test data was used during training/selection
