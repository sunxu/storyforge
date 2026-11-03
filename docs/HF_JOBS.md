# Hugging Face Jobs: adradar

Private bucket: `hf://buckets/adradar/storyforge-training`

## CPU-only Jobs: namespace, permissions and mount policy

All StoryForge Jobs use the organization namespace `adradar` and the private project
bucket `hf://buckets/adradar/storyforge-training`. The authenticated user identity
and the billing namespace are distinct: an account can authenticate as
`greenkeedle` while submitting a Job to organization namespace `adradar`.

### Required mount topology

Do not mount the entire bucket read-write. Use a read-only source mount and a
separate writable output prefix:

```text
hf://buckets/adradar/storyforge-training/<private-input-prefix>:/input/<filename>:ro
hf://buckets/adradar/storyforge-training/<worker-script-prefix>:/scripts/<filename>:ro
hf://buckets/adradar/storyforge-training/<unique-output-prefix>:/output:rw
```

- All input and worker-code mounts are explicitly `:ro`.
- SAFE reports and logs go to a separate, unique `:rw` output prefix.
- Never use the same source prefix for input and output.
- Use a new output prefix for every attempt; do not overwrite earlier evidence.
- Do not omit the mode suffix and rely on a default.
- Use `--attempts 1`; retries require inspection and a deliberate new attempt.

### Guarded CPU submission

Use `scripts/hf_job_guard.py`. It is a policy gate and submit wrapper, not a
credential manager. It runs `hf auth whoami` before a real submission and invokes
the Hugging Face CLI with an argument array (not shell interpolation).

Example preflight (no Job is created):

```bash
python3 scripts/hf_job_guard.py \\
  --namespace adradar \\
  --name storyforge-r59-cpu-collator \\
  --flavor cpu-basic \\
  --timeout-minutes 15 \\
  --input-volume 'hf://buckets/adradar/storyforge-training/preflight/r59/20261103/R59_SFT_SHAPE_PREVIEW_PRIVATE.jsonl:/input/R59_SFT_SHAPE_PREVIEW_PRIVATE.jsonl:ro' \\
  --input-volume 'hf://buckets/adradar/storyforge-training/scripts/r59_sft_collator_cpu.py:/scripts/r59_sft_collator_cpu.py:ro' \\
  --output-volume 'hf://buckets/adradar/storyforge-training/preflight/r59/20261103/reports/attempt-<unique-id>:/output:rw' \\
  --image python:3.11 \\
  -- python3 /scripts/r59_sft_collator_cpu.py \\
     --private-input /input/R59_SFT_SHAPE_PREVIEW_PRIVATE.jsonl \\
     --output-safe /output/R59_ACTUAL_SWIFT_COLLATOR_SAFE.json
```

For the R59 Qwen collator specifically, the worker must resolve only this
immutable model revision:

```text
Qwen/Qwen3.8-27B
1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0
```

The collator uses ms-swift `get_processor(..., revision=<SHA>)`; a SAFE report
must state `model_revision_pinned: true`. A report that does not confirm the
revision pin is a HOLD, not a successful preflight.

After reviewing the SAFE preflight result, add `--submit` before the `--`
separator to create the CPU Job. The tool enforces:

- namespace exactly `adradar`;
- CPU flavor `cpu-basic` or `cpu-upgrade` only;
- timeout between 1 and 120 minutes;
- one or more read-only input/script mounts;
- one separate read-write `/output` mount;
- exactly one submission attempt;
- no automatic personal-namespace fallback and no GPU selection.

The caller is responsible for choosing a fresh output prefix and a command that
writes SAFE-only output under `/output`. Private input text must not be printed
to Job logs. A successful submission response is not proof that the Job completed;
inspect its status, logs, and output receipt separately.

### Failure handling

| Result | Required response |
|---|---|
| HTTP 403 | Stop. Check organization permission and mount mode. Do not retry with broader permissions or an RW input mount. |
| HTTP 402 | Stop. Check billing for the explicitly selected namespace. Do not switch to the personal namespace. |
| CLI/authentication failure | Stop and repair authentication; do not change namespace as a workaround. |
| Job runtime failure | Preserve the Job ID and logs. Correct the cause and use a new unique output prefix for a deliberate new attempt. |

A failed submission must never trigger automatic namespace switching, permission
broadening, mount-mode broadening, retries, or GPU escalation.

### Verified regression history (2026-11-01)

The following configuration outcomes were observed in the prior troubleshooting:

- `adradar` + `cpu-basic` without a Bucket mount: the authenticated CPU Jobs
  check completed with Job `6ae6f7710e0338d1bb7d6434`.
- `adradar` + `cpu-basic` with a private Bucket mounted `:ro`: Job
  `6ae6fc3dc78863f9c62f8556` submitted successfully.
- `adradar` + `cpu-upgrade` with a private Bucket mounted `:ro`: Job
  `6ae6fc6cc78863f9c62f855c` submitted successfully.
- The corresponding private Bucket `:rw` input-mount probe returned HTTP 403.
- A separate authenticated CPU Jobs check in organization namespace `adradar`
  completed with Job `6ae6f7710e0338d1bb7d6434`.

These results establish the previously tested namespace/flavor/mount combinations;
they do not guarantee current organization billing availability. The R59 CPU
collator must use the same read-only-input/separate-writable-output topology.

## Local submission (GPU charges only after --submit)

Install the Hugging Face CLI and log in first. On your Mac:

```bash
git pull
pip install -U huggingface_hub
bash scripts/hf_submit_smoke.sh
```

The default command uploads the local v0.3 train and validation files and job scripts/configuration into the private bucket, **without provisioning a GPU**. It does not upload the held-out test file.

Check the files and billable Job parameters. Then explicitly submit:

```bash
bash scripts/hf_submit_smoke.sh --submit
```

The job uses `a100-large` with a 45-minute timeout. This is a maximum runtime, not an estimate. Model download/dependency install count toward GPU time. The Job is not guaranteed to finish within that window.

Query logs with `hf jobs logs adradar/JOB_ID`. Run artifacts are stored in `runs/JOB_ID/` in the bucket; the unique Job ID prevents one run overwriting another.

The job prepares separate train/validation copies with `loss: false` on all earlier assistant messages and `loss: true` only on the final selected response. It then audits every sample using the installed ms-swift template. Any audit failure stops the job before training. Runtime checks also reject incorrect loss strategy or missing 4-bit bfloat16 quantization.

## Safety and acceptance

- The test split is never sent to `swift sft`.
- The command intentionally does not use `--delete` when syncing buckets.
- It does not create a GPU job without `--submit`.
- A `SUCCESS` marker requires three completed steps, finite training and validation losses, saved adapter weights, and a separate adapter reload/inference process producing a nonempty response.
- The runner pins ms-swift 4.5.3 and transformers 5.16.1. It records the base Git commit and SHA256 of the actual uploaded scripts/config; local changes can therefore be distinguished from that commit.
- Do not automatically destroy the Bucket. It is the persistence layer.
- Check the exact ms-swift arguments and CUDA dependency compatibility in the remote logs.
- For lower costs, build a pinned Docker image and warm the base model/cache before repeated GPU training.
- Running under HF Jobs has no guarantee that a terminated process will flush the last checkpoint. Save early and consider periodic syncing/verification.

### GitHub Actions runner-allocation failures

If a workflow job reports `runner_id: 0`, `steps: []`, and completes before any
step starts, the runner was not allocated and the workflow did not execute the
repository tests. Treat this as an infrastructure/runner-allocation failure,
not a code PASS or a code-level test failure. Preserve the run URL and retry
only after the GitHub Actions runner service is available. Do not use a failed
pre-runner check as evidence that the change passed CI.

