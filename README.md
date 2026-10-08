# StoryForge

StoryForge is an experimental training and evaluation pipeline for interactive narrative language models.

The initial target is Qwen3.8-27B with SFT / QLoRA, using curated multi-turn story data with character profiles, world state, conversation history, and gold responses.

## Project goals

- Compile raw story transcripts into reproducible training datasets
- Prevent future-state / label leakage during dataset construction
- Fine-tune narrative models with SFT / QLoRA
- Evaluate character consistency, plot continuity, agency, formatting, and narrative quality
- Version datasets, training configs, adapters, and evaluation results

## Planned structure

```text
storyforge/
├── configs/        # Training configs
├── data/           # Local/raw/compiled datasets (large/private data ignored by Git)
├── eval/           # Gold evaluation sets and evaluation scripts/results
├── scripts/        # Dataset compiler, validation, training utilities
├── .github/        # GitHub Actions workflows
└── README.md
```

## Status

Project initialization.
