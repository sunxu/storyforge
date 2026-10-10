# StoryForge Dataset Management

## Overview

StoryForge maintains versioned datasets for interactive narrative language model training and evaluation.

The accepted StoryForge model v0.1 baseline uses **Dataset v0.3**.

Dataset version numbers are independent of model version numbers.

## Dataset v0.3 — Accepted Baseline

- Base model: `Qwen/Qwen3.8-27B`
- Dataset version: `v0.3`
- Total selected Gold samples: **100**
- Train: **65**
- Validation: **15**
- Held-out Test: **20**
- Split isolation: by `story_id`
- Maximum context length: **16,384 tokens**
- Supervision: final Gold assistant response only
- Historical assistant, system and user messages: not supervised

The dataset has passed basic structural validation and story-level split isolation checks.

Training label-mask and token-budget verification are documented separately in the project's accepted engineering evidence.

## Directory Structure

```text
data/
├── README.md
├── raw/
│   └── 100条作品回答范例_完整上下文_JSONL_20260930/
├── private/
└── compiled/
    ├── v0.1/
    ├── v0.2/
    └── v0.3/
        ├── train.jsonl
        ├── validation.jsonl
        ├── test.jsonl
        ├── budget_report.json
        ├── token_report.json
        └── SHA256SUMS.txt
```

The `private/` directory is reserved and may not exist locally.

Dataset v0.3 does not currently contain a `manifest.json`. Do not fabricate one.

## Git Tracking Policy

### Raw Source Data

`data/raw/` remains Git-ignored.

It contains original story exports, transcripts, metadata and selected Gold responses.

Raw exports must undergo a separate content, privacy and publication-rights review before public archival.

### Private Data

`data/private/` must never be committed as a complete directory.

Access credentials, authentication tokens, private keys and sensitive personal information must not enter Git history.

### Compiled Datasets

`data/compiled/` remains Git-ignored by default.

The following files constitute the explicitly selected Dataset v0.3 archive:

- `train.jsonl`
- `validation.jsonl`
- `test.jsonl`
- `budget_report.json`
- `token_report.json`
- `SHA256SUMS.txt`

These files may be force-added to Git only after content review and publication authorization.

Historical compiled Dataset v0.1 and v0.2 directories are excluded from this archival scope.

## Dataset v0.3 Integrity

The following SHA256 hashes were reported by the local Dataset v0.3 basic audit.

| File | SHA256 |
|---|---|
| `train.jsonl` | `9a24f07befee9e701c587f4b154b0e780c29534abe3a0fa8b0c310511172a60f` |
| `validation.jsonl` | `083a6f124abc414a0edf268d1a95788f738d55e7ecd229a78c67087991f46c36` |
| `test.jsonl` | `d8eee6db5882d85dce7ffc01256e7c5b9b46e133bdb2cf8591259112b92e980d` |

The Test SHA256 also matches the previously archived canonical Gold reconciliation evidence.

Train and Validation hashes represent local file verification; byte-level correspondence with the original remote HF training inputs has not yet been independently established.

The `SHA256SUMS.txt` file records the exact checksums of the complete six-file archive's five data/report inputs.

## Verify Dataset Integrity

Run from the repository root:

```bash
shasum -a 256 -c data/compiled/v0.3/SHA256SUMS.txt
```

All five checks must pass.

## Rebuild From Raw Data

The original raw export is retained outside Git.

Validate the source:

```bash
storyforge-dataset validate \
  data/raw/100条作品回答范例_完整上下文_JSONL_20260930 \
  --expected-selected 100
```

The historical Dataset v0.1 compilation example used:

```bash
storyforge-dataset compile \
  data/raw/100条作品回答范例_完整上下文_JSONL_20260930 \
  --output data/compiled/v0.1 \
  --history-messages 12
```

This historical command does not by itself reproduce the accepted Dataset v0.3.

Any claimed v0.3 reconstruction must use the matching compiler revision and frozen compilation parameters, and the resulting files must be verified against the accepted SHA256 manifest.

## Training Provenance

StoryForge model v0.1 baseline:

- Hugging Face Job: `6ac75bafdf2184ac91acb293`
- Base model: `Qwen/Qwen3.8-27B`
- Training method: QLoRA / SFT
- Accepted model training: PASS
- Model quality promotion: NOT APPROVED

The frozen v0.1 historical evidence is preserved at:

`v0.1-evidence-frozen`

Commit:

`d1186a731a81219f86eb81b89ac1440dd116e9f4`

Publishing Dataset v0.3 to `main` does not alter this immutable historical tag.

## Publication and Reproducibility Policy

Dataset publication requires:

1. Structural and split-isolation validation.
2. SHA256 verification.
3. Credential and sensitive-information screening.
4. Review of story-content publication rights.
5. Explicit confirmation that the selected files are authorized for public distribution.

Original evidence must not be silently modified after archival.

Any corrected dataset must receive a separately documented revision with new file hashes.
