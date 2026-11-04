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

### 2.2.1 R59 context-window rebuild policy

The R59 16K context-window rebuild is a separate, explicit engineering step; the
original shape-preview builder MUST continue preserving the complete source
history. Never rewrite or overwrite the original Preview.

- Pin `Qwen/Qwen3.8-27B@1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0` and
  `max_length=16384`; measure in Hugging Face CPU with ms-swift, not on the Mac.
- Keep the approved System Prompt and final target Assistant bytes unchanged.
- If the full history does not fit, remove only a leading prefix and begin the
  retained suffix at a complete User-message boundary. Preserve every later
  message in its original order; never delete middle messages or truncate text.
- Preserve the final User and target Assistant messages. Historical messages
  remain `loss=false`; only the final target remains `loss=true`.
- Preserve the original input-context SHA as provenance and recompute
  `input_messages_sha256` over the retained context.
- Use `experiments/r58_quality/r59_sft_context_window.py`; it reuses the
  existing preview validator and actual ms-swift Collator, and uses the shared
  `extract_input_ids` core. For standalone HF Jobs, mount the scripts directory
  and provide `token_core.py` as an exact byte-for-byte copy of
  `src/storyforge_dataset/token_preflight.py`.
- Any sample whose current User + target or complete eligible suffix cannot fit
  MUST HOLD. The operation is all-or-none for a batch and writes a new private
  create-only output; it never mutates source input.
- Context-window and actual Collator PASS are engineering checks only:
  `quality_v1_admitted=0`, `dataset_frozen=false`,
  `training_authorized=false`, `gpu_started=false` remain mandatory.
- Chinese execution runbook: `docs/R59_CONTEXT_WINDOW_CN.md`.

### 2.2.2 HF Jobs Runtime Skill

Before creating or changing any HF Job Runner, read `skills/storyforge-hf-jobs/SKILL.md` and its relevant references. Use `storyforge_dataset.hf_runtime` for shared context, paths, input/output, diagnostics, resources and receipt validation. Business-specific behavior belongs in thin adapters. Keep `src/storyforge_dataset/token_preflight.py` unchanged and reuse it as the only tokenizer core. The complete operational standard is `docs/standards/HF_JOBS_ENGINEERING.md`.

### 2.3 Hugging Face Jobs namespace and volume policy

StoryForge Hugging Face Jobs MUST use the organization namespace `adradar` and the
project bucket `hf://buckets/adradar/storyforge-training`. Do not silently fall back
to the personal namespace `greenkeedle` after an organization submission error.

For CPU jobs, use separate mounts:

- Every source/input mount MUST be explicitly read-only (`:ro`), mounted below
  `/input/` or `/scripts/`.
- The output mount MUST be a separate project-bucket prefix mounted at `/output`
  with explicit read-write mode (`:rw`).
- Never mount the whole project bucket read-write as a shortcut.
- Never make the output mount read-only; SAFE reports need a dedicated writable
  destination.
- Use a unique output prefix for each attempt to prevent overwriting prior receipts.

Use `scripts/hf_job_guard.py` for CPU submissions. It enforces namespace
`adradar`, CPU-only flavors, a bounded timeout, read-only inputs, one separate
read-write output, and one attempt. Without `--submit`, it performs validation only.
The tool does not fall back to a personal namespace, retry automatically, or submit
GPU jobs.

Known incident regression rules:

- HTTP 403 with a read-write source/input mount: inspect mount mode and organization
  permissions. The previously reproduced bucket-mount failure was resolved by
  mounting the input prefix `:ro` and using a separate output prefix `:rw`.
- HTTP 402 in the personal namespace: do not infer that the organization is out of
  balance and do not switch billing namespaces. Check the intended organization
  billing/permission state.
- A 403/402 MUST NOT trigger automatic namespace fallback, permission broadening,
  mount-mode broadening, retries, or GPU escalation.

A 403 from the ChatGPT HF connector MUST NOT be treated as proof that the
Mac-local HF CLI is broken. The 2026-11-01 Mac-local private Bucket RW smoke
and sync-back passed. For connector-only 403s, stop connector retries and use
the documented guarded Mac-local CLI route in `docs/HF_JOBS.md`; never
reconnect/retry blindly or change namespaces/mount permissions as a workaround.

The 2026-11-04 ChatGPT HF connector probe verified that organization CPU
submission and private Bucket RO mounts work, while private Bucket RW mounts
still return HTTP 403. For SAFE-only CPU preflights, prefer RO inputs and emit
only the SAFE aggregate receipt to Job stdout/logs; never print private sample
content. Mount a Bucket directory prefix (not an assumed file mount), then
assert the expected file with `test -f` before reading it. See the 2026-11-04
regression and mount-semantics sections in `docs/HF_JOBS.md`.

For the R59 Qwen3.8-27B ms-swift Python preflight, set
`USE_HF=true` before importing Swift because the pinned revision is a
Hugging Face commit SHA; ms-swift defaults to ModelScope otherwise. Install
`qwen-vl-utils==0.0.14`, `decord`, and `torchvision==0.29.2` for the
Qwen processor. See the R59 runtime contract in `docs/HF_JOBS.md`.

See `docs/HF_JOBS.md` for the verified incident record and invocation contract.

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
