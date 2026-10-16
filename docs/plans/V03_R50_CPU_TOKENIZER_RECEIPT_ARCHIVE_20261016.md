# R50 46-case tokenizer CPU Job receipt — 2026-10-16

The owner supplied terminal evidence that **HF Job `6ad1fd155ccb47ba0f7b1ec6` finished**
with `R50_TOKENIZER_PREFLIGHT__BUDGET_PASS` and `CPU_TOKENIZER_PREFLIGHT_DONE__NO_INFERENCE__NO_GPU__NO_FINAL_SEAL`.

This is **owner-reported remote success**. ChatGPT has not authenticated to the
private HF Bucket or independently read its complete per-case JSON report.
Do not label this receipt as independently-verified 46/46 until the Git-native
verifier below has run against the actual bytes.

Raw report remains in the private HF Bucket at the known job stage.
Run from the existing authenticated Mac checkout, with no file handoff to chat:

```bash
cd ~/workspace/storyforge
git fetch origin audit/r49-r50-source-intake-20261015
git switch audit/r49-r50-source-intake-20261015
git pull --ff-only

# All tests use synthetic data, no HF Job or model inference:
python3 -m unittest discover -s tests -p 'test_v03_r50_tokenizer_receipt.py' -v

# Use the stage key saved from your successful HF run, without committing it:
R50_STAGE_KEY='your-existing-r50-token-...-key'

# Read and validate the private HF report; print aggregate only, no Git mutation:
python3 scripts/v03_r50_verify_and_archive_tokenizer.py \
  --stage-key $R50_STAGE_KEY \
  --job-id 6ad1fd155ccb47ba0f7b1ec6

# After validation, explicitly push ONLY the sanitized aggregate to this audit branch:
python3 scripts/v03_r50_verify_and_archive_tokenizer.py \
  --stage-key $R50_STAGE_KEY \
  --job-id 6ad1fd155ccb47ba0f7b1ec6 --push
```

The script makes an ephemeral authenticated `hf buckets cp` internally, checks
the report's 46 records, 364 historical messages, 12 consecutive-user cases,
five-world counts, pinned model/tokenizer/System/candidate hashes, disabled
thinking mode, 16,384-token total budget with 1,536 tokens reserved, and zero
overflows. It writes only aggregate distribution statistics and a whole-report
SHA256; it does **not** write cases or raw narratives into ordinary Git.

Passing a tokenizer budget does **not** independently prove semantic world
isolation, approved four-arm input parity, final test sealing, or model quality
promotion. All remain separate review gates. No GPU or paid HF Job is launched
by this validator.
