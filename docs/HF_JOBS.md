# Hugging Face Jobs: adradar

Private bucket: `hf://buckets/adradar/storyforge-training`

## Local submission (GPU charges only after --submit)

Install the Hugging Face CLI and log in first. On your Mac:

```bash
git pull
pip install -U huggingface_hub
bash scripts/hf_submit_smoke.sh
```

The default command syncs local Dataset v0.3 and job scripts/configuration into the private bucket, **without provisioning a GPU**.

Check the files and billable Job parameters. Then explicitly submit:

```bash
bash scripts/hf_submit_smoke.sh --submit
```

The job uses `a100-large` with a 45-minute timeout. This is a maximum runtime, not an estimate. Model download/dependency install count toward GPU time. The Job is not guaranteed to finish within that window.

Query logs with `hf jobs logs adradar/JOB_ID`. Run artifacts are stored in `runs/JOB_ID/` in the bucket; the unique Job ID prevents one run overwriting another.

The job prepares a separate train/validation dataset with `loss: false` on all earlier assistant messages and `loss: true` only on the final selected response. This encodes the intended target-only supervision, but **verify the actual ms-swift collator labels** before considering the pipeline fully accepted.

## Safety and acceptance

- The test split is never sent to `swift sft`.
- The command intentionally does not use `--delete` when syncing buckets.
- It does not create a GPU job without `--submit`.
- A `SUCCESS` marker only indicates a zero-exit training command; LoRA reload and generation still need to be tested.
- Do not automatically destroy the Bucket. It is the persistence layer.
- Check the exact ms-swift arguments and CUDA dependency compatibility in the remote logs.
- For lower costs, build a pinned Docker image and warm the base model/cache before repeated GPU training.
- Running under HF Jobs has no guarantee that a terminated process will flush the last checkpoint. Save early and consider periodic syncing/verification.
