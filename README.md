# StoryForge

StoryForge is an experimental training and evaluation pipeline for interactive narrative language models, initially targeting `Qwen/Qwen3.8-27B` with SFT / QLoRA and curated multi-turn stories.

## Project status (2026-10-09)

**v0.1 engineering: PASS. Model-quality promotion: NOT APPROVED.** Training and both held-out human review rounds are complete. The v0.1 evidence is frozen at Git tag [`v0.1-evidence-frozen`](https://github.com/sunxu/storyforge/tree/v0.1-evidence-frozen), commit `d1186a731a81219f86eb81b89ac1440dd116e9f4`.

- Dataset v0.3: 19 stories / 23 transcripts / 100 selected Gold examples.
- Story-isolated sample split: **65 train / 15 validation / 20 test**.
- Baseline: Qwen3.8-27B, rank64 QLoRA NF4 BF16, 1 epoch, 9 optimizer steps, saved adapter checkpoint-9.
- Validation: 15 A/B samples; held-out test: 20 A/B samples with two independent review rounds and arbitration.
- Held-out round 1: Base 13 wins / Adapter 7; round 2: Base 10 / Adapter 10.
- v0.1 adapter has **not demonstrated a stable overall improvement** over Base. Do not promote it to default production model on this evidence.
- Next milestone: **v0.2 / Dataset v0.4** — new story-isolated Gold data and a genuinely new held-out set, with failure taxonomy and predeclared acceptance criteria.

### Start here

- [v0.1 final handoff](docs/V01_FINAL_HANDOFF.md)
- [Hugging Face Job & artifact index](docs/HF_RUN_REGISTRY.md)
- [Frozen two-round evaluation evidence](evaluations/v0.1/README.md)
- [Baseline engineering acceptance](docs/evidence/BASELINE_SFT_V01_20261008.md)
- [Held-out test execution protocol (historical)](docs/HELDOUT_TEST_V01.md)

The frozen 20-sample test has now been disclosed and analyzed. It remains useful as a retrospective diagnostic benchmark, **not** as a new unseen v0.2 generalization test.

## Repository structure

```text
storyforge/
├── .github/workflows/   # CI
├── configs/             # Training configurations
├── data/                # Local raw and compiled training data (gitignored)
├── docs/                # Contracts, training evidence, handoff, HF Job registry
├── eval/                # Evaluation support
├── evaluations/v0.1/    # Publicly archived v0.1 blind evaluation evidence
├── scripts/             # Training/evaluation tools
├── src/storyforge_dataset/
├── tests/
└── pyproject.toml
```

## Local setup

```bash
git clone https://github.com/sunxu/storyforge.git
cd storyforge
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,analysis]"
```

## Data provenance and safety

Dataset compilation is story-isolated: source messages after the target are excluded from prompts, and only the final selected Gold assistant response is supervised. See [dataset contract](docs/DATASET_V0_1.md) and current training config.

The user explicitly authorized public archiving of completed v0.1 evaluation materials. The original story training exports, large compiled datasets, model weights and adapters are not stored as Git objects; actual API credentials, HF access tokens and private keys must never be committed.

The authoritative v0.1 acceptance record is the immutable frozen tag; later `main` documentation updates do not alter its contents.
