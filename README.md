# StoryForge

StoryForge is an experimental training and evaluation pipeline for interactive narrative language models.

The initial target is Qwen3.8-27B with SFT / QLoRA, using curated multi-turn story data with character profiles, world state, conversation history, and gold responses.

## Current milestone

Dataset v0.1 compiler is in place.

Verified against the 2026-09-30 complete-context export:

- 19 stories
- 23 transcripts
- 795 content messages
- 100 selected gold assistant targets
- deterministic story-level split: 15 train / 2 validation / 2 test
- compiled sample split: 65 train / 15 validation / 20 test
- future messages and target metadata are excluded from prompt construction

## Project goals

- Compile raw story transcripts into reproducible training datasets
- Prevent future-state / label leakage during dataset construction
- Fine-tune narrative models with SFT / QLoRA
- Evaluate character consistency, plot continuity, agency, formatting, and narrative quality
- Version datasets, training configs, adapters, and evaluation results

## Structure

```text
storyforge/
├── .github/workflows/   # CI and later training workflows
├── configs/             # Training configs
├── data/                # Local raw/compiled data; private data is gitignored
├── docs/                # Dataset and training contracts
├── eval/                # Gold evaluation sets and evaluation tooling
├── scripts/             # Future training/evaluation utilities
├── src/
│   └── storyforge_dataset/
├── tests/
├── pyproject.toml
└── README.md
```

## Local setup

```bash
git clone https://github.com/sunxu/storyforge.git
cd storyforge

python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,analysis]"
```

Put the extracted private export under `data/raw/`. It is intentionally excluded from Git.

Validate it:

```bash
storyforge-dataset validate \
  data/raw/100条作品回答范例_完整上下文_JSONL_20260930 \
  --expected-selected 100
```

Compile Dataset v0.1:

```bash
storyforge-dataset compile \
  data/raw/100条作品回答范例_完整上下文_JSONL_20260930 \
  --output data/compiled/v0.1 \
  --history-messages 12
```

Output:

```text
data/compiled/v0.1/
├── train.jsonl
├── validation.jsonl
├── test.jsonl
└── manifest.json
```

Analyze token budget with the exact target tokenizer/chat template:\n\n```bash\nstoryforge-dataset analyze \\\n  data/compiled/v0.1 \\\n  --model Qwen/Qwen3.8-27B\n```\n\nThis writes `data/compiled/v0.1/token_report.json` and reports P50/P90/P95/P99, 4K/8K/16K fit rates, the 10 largest samples, and a recommended `max_length`.\n\nSee `docs/DATASET_V0_1.md` for the leakage and split contract.

## Status

- Repository initialization: complete
- Raw dataset contract: complete
- Dataset v0.1 validator/compiler: complete
- CI: enabled
- Token-budget analysis: next
- Qwen3.8-27B smoke training config: next
