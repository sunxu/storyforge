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

### 2.1 Hugging Face execution boundary

All model-specific Tokenizer, Chat Template, token-budget and tokenizer/model-revision preflights MUST run in a Hugging Face CPU environment, not on the user's Mac. The Mac may prepare files, verify file integrity, stage/sync private inputs and inspect SAFE receipts; do not instruct the user to run model-specific tokenization locally.

- Pin the exact model ID, immutable revision and relevant runtime/template versions to the intended workload.
- Keep source text, world cards, blind-review packets, derived prompts, Owner crosswalks and case-level receipts in private storage. Do not expose them in GitHub, Job logs or chat.
- Outside private storage, emit only SAFE aggregate results. Never silently truncate history, modify frozen Gold, or treat Token PASS as literary quality approval or training admission.
- When the user explicitly requests a workflow requiring CPU tokenization/preflight, use the minimum necessary HF CPU execution within the requested scope; no separate per-Job cost authorization is required. This does not authorize GPU inference or training, which still require separate explicit approval.

### 2.2 Shared tooling policy

StoryForge has one shared Token preflight implementation: `src/storyforge_dataset/token_preflight.py`. New project-specific workflows must reuse it and keep differences in thin adapters; do not copy the shared algorithm into Skills, workers or round-specific scripts.

The complete technical contract—including adapter boundaries, cache identity, SAFE diagnostics, staging, verification and historical compatibility—is maintained in `docs/standards/HF_TOKEN_PREFLIGHT_REUSE_CN.md`. Follow the R58 Skill's execution order before changing tooling. Keep historical frozen scripts, private inputs, receipts and checkpoints unchanged.

Generic tokenizer checks do not replace real ms-swift `last_round` / data-collator label-mask validation. Neither kind of PASS independently grants literary quality admission or training authorization.

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

#### Mandatory historical-implementation reuse check

Before designing, implementing, refactoring, or adding a new tool, **read [docs/REUSABLE_ASSET_INDEX.md](docs/REUSABLE_ASSET_INDEX.md)** and search `main`, existing shared modules/tests, pinned archives and relevant historical branches. Do not assume closed PRs or archived implementations are already present on `main`.

- Record the inspected `ref@commit:path`, whether an equivalent exists on `main`, the actual gap, and the reuse-vs-new-code decision in the PR or next-Agent handoff. If the search is incomplete, establish provenance before building an alternative.
- **Prefer reuse and the minimum compatible change.** Use existing APIs/shared cores; selectively transplant only necessary files or reviewed commits. Do not merge an entire historical experimental branch, duplicate a Runtime/evaluation/reconciliation framework, or revive an abandoned workflow just to satisfy a new task.
- Recheck dependency compatibility, regression tests, private-data boundaries, historical source provenance, and Owner approval. A past CI PASS, GPU profile freeze, test receipt, closed PR, or SAFE report is **not** new authorization for model inference, training, deployment, admission, promotion, or R61 work.
- `archive/*` refs are immutable historical sources, not automatic production baselines. Local-only `backup/*` refs may be unavailable to new Agents. Update the asset index when an important reusable implementation is added, superseded, or moved.

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

### 5.1 Artifact delivery (GitHub first)

For project code, tests, standards, runbooks and SAFE receipts, deliver changes through the existing GitHub feature branch / PR with commit SHA and validation status. Do not package tools as ZIP by default. ZIP is reserved for an explicit user request for compressed/offline handoff. Keep PRIVATE records and per-case review queues out of GitHub. See `docs/standards/PROJECT_ARTIFACT_DELIVERY_GITHUB_FIRST_CN.md`.

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
