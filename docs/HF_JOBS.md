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
python3 scripts/hf_job_guard.py \
  --namespace adradar \
  --name storyforge-r59-cpu-collator \
  --flavor cpu-basic \
  --timeout-minutes 15 \
  --input-volume 'hf://buckets/adradar/storyforge-training/preflight/r59/20261103/R59_SFT_SHAPE_PREVIEW_PRIVATE.jsonl:/input/R59_SFT_SHAPE_PREVIEW_PRIVATE.jsonl:ro' \
  --input-volume 'hf://buckets/adradar/storyforge-training/scripts/r59_sft_collator_cpu.py:/scripts/r59_sft_collator_cpu.py:ro' \
  --output-volume 'hf://buckets/adradar/storyforge-training/preflight/r59/20261103/reports/attempt-r59-cpu-02:/output:rw' \
  --image python:3.11 \
  -- /bin/sh -lc 'set -eu
export CUDA_VISIBLE_DEVICES=""
export USE_HF=true
export TOKENIZERS_PARALLELISM=false
python3 -m pip install --no-cache-dir "ms-swift==4.5.3" "transformers==5.16.1" "qwen-vl-utils==0.0.14" decord "torchvision==0.29.2"
cp /input/R59_SFT_SHAPE_PREVIEW_PRIVATE.jsonl /tmp/R59_SFT_SHAPE_PREVIEW_PRIVATE.jsonl
chmod 600 /tmp/R59_SFT_SHAPE_PREVIEW_PRIVATE.jsonl
timeout --signal=TERM --kill-after=20s 780s python3 /scripts/r59_sft_collator_cpu.py \
  --private-input /tmp/R59_SFT_SHAPE_PREVIEW_PRIVATE.jsonl \
  --output-safe /output/R59_ACTUAL_SWIFT_COLLATOR_SAFE.json'
```

For the R59 Qwen collator specifically, set `USE_HF=true` before importing
ms-swift. ms-swift 4.5.3 defaults to ModelScope (`USE_HF=False`); the pinned
revision below is a Hugging Face commit SHA. The 2026-11-04 ChatGPT CPU probe
reproduced an `HTTPError` in `get_processor` when ms-swift attempted to resolve
that SHA through ModelScope. Setting `USE_HF=true` resolved the exact 23.1 MB
Hugging Face snapshot at the pinned SHA. The Qwen processor also requires
`qwen-vl-utils==0.0.14`, `decord`, and `torchvision==0.29.2` in the tested Python 3.11 environment. The Qwen processor import then has its required vision dependency without changing the pinned `torch` package selected by ms-swift.

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

### Connector 403 versus Mac-local CLI (verified 2026-11-01)

A 403 returned by the ChatGPT Hugging Face Jobs connector is not proof that
the Mac-local Hugging Face CLI has the same failure. Keep the two submission
identities and execution paths separate.

The following Mac-local path was verified:

- `hf auth whoami` authenticated the account with access to organization
  namespace `adradar`.
- A private Bucket read/write smoke Job completed as
  `6ae727c70e0338d1bb7d7258` and wrote `HF PRIVATE RW SMOKE PASS`.
- The output was synchronized back with `hf buckets sync` and verified locally.
- Both A/B output sync-back checks passed.

When the ChatGPT connector returns 403 for a private Bucket RW mount, do not
repeatedly reconnect OAuth or retry the same connector request. Do not infer
that local CLI submission is broken. Verify the local identity with
`hf auth whoami`, list existing organization Jobs before submitting, then use the
guarded local CLI route below. Never print tokens or credentials.

#### R59 CPU Collator: Mac-local submission

Run from the StoryForge repository root on the Mac. First verify the exact
branch and local authentication:

```bash
set -euo pipefail
test "$(git branch --show-current)" = "gold-quality/quality-v1-sft-candidates"
hf auth whoami
hf jobs ls -a --namespace adradar
```

Then submit one CPU-only attempt using the existing guard. Use a fresh output
prefix for each deliberate attempt; this example is the 2026-11-04 first
Mac-local attempt:

```bash
.venv/bin/python scripts/hf_job_guard.py \
  --namespace adradar \
  --name storyforge-r59-collator-cpu \
  --flavor cpu-basic \
  --timeout-minutes 15 \
  --input-volume 'hf://buckets/adradar/storyforge-training/preflight/r59/20261103/R59_SFT_SHAPE_PREVIEW_PRIVATE.jsonl:/input/R59_SFT_SHAPE_PREVIEW_PRIVATE.jsonl:ro' \
  --input-volume 'hf://buckets/adradar/storyforge-training/scripts/r59_sft_collator_cpu.py:/scripts/r59_sft_collator_cpu.py:ro' \
  --output-volume 'hf://buckets/adradar/storyforge-training/preflight/r59/20261104/reports/collator-cpu-mac-01:/output:rw' \
  --image python:3.11 \
  --submit \
  -- /bin/sh -lc 'set -eu
export CUDA_VISIBLE_DEVICES=""
export TOKENIZERS_PARALLELISM=false
python3 -m pip install --no-cache-dir "ms-swift==4.5.3" "transformers==5.16.1"
cp /input/R59_SFT_SHAPE_PREVIEW_PRIVATE.jsonl /tmp/R59_SFT_SHAPE_PREVIEW_PRIVATE.jsonl
chmod 600 /tmp/R59_SFT_SHAPE_PREVIEW_PRIVATE.jsonl
timeout --signal=TERM --kill-after=20s 780s python3 /scripts/r59_sft_collator_cpu.py \
  --private-input /tmp/R59_SFT_SHAPE_PREVIEW_PRIVATE.jsonl \
  --output-safe /output/R59_ACTUAL_SWIFT_COLLATOR_SAFE.json'
```

The guard invokes the Mac-local `hf` executable with one attempt and explicit
`adradar` namespace. Do not resubmit if the command's outcome is uncertain;
first inspect `hf jobs ls -a --namespace adradar` and locate the existing Job.

After the Job completes, retrieve its logs and synchronize only the SAFE report:

```bash
hf jobs ls -a --namespace adradar
# Replace JOB_ID with the ID returned by the successful submission.
hf jobs logs adradar/JOB_ID

mkdir -m 700 -p "$HOME/.local/share/storyforge/r59/private/collator-cpu-mac-01"
hf buckets sync \
  hf://buckets/adradar/storyforge-training/preflight/r59/20261104/reports/collator-cpu-mac-01 \
  "$HOME/.local/share/storyforge/r59/private/collator-cpu-mac-01"
chmod 600 "$HOME/.local/share/storyforge/r59/private/collator-cpu-mac-01/R59_ACTUAL_SWIFT_COLLATOR_SAFE.json"
```

Verify the synchronized receipt locally before reporting PASS. Required result:
`R59_ACTUAL_SWIFT_COLLATOR_PASS__NOT_ADMITTED`, five checked/five passed,
`model_revision_pinned: true`, `gpu_used: false`, and
`training_performed: false`. A Job submission or successful exit alone is
not acceptance. No Quality-v1 admission, dataset freeze, inference or training
is authorized by this CPU preflight.

### ChatGPT connector submission regression (verified 2026-11-04)

A fresh ChatGPT HF connector OAuth context authenticated as `greenkeedle`,
showed organization `adradar` with role `write`, and successfully submitted
CPU Jobs into `adradar`. Isolated probes established:

- No-volume CPU Job submission: PASS.
- Private project Bucket mounted read-only (`:ro`): PASS.
- Private project Bucket mounted read-write (`:rw`) through the ChatGPT
  connector: HTTP 403.
- Therefore the current connector regression is specifically associated with
  the RW Bucket mount path, not general Jobs authorization or RO access.

For ChatGPT-side CPU preflights that produce SAFE-only aggregate receipts, use
read-only Bucket mounts and print the SAFE JSON receipt to Job stdout/logs.
Do not mount a writable Bucket solely to persist a SAFE aggregate. Do not print
private sample text, prompts, identifiers, or token IDs. Retrieve logs using
the connector's Jobs log operation with both `job_id` and
`namespace="adradar"`. This is a temporary, evidence-backed workaround; it
does not resolve the connector's RW mount 403.

### Bucket subpath mount semantics (verified 2026-11-04)

Mount a Bucket directory prefix, not a file path, when the worker expects a
regular file below the mount point. For example:

```text
hf://buckets/adradar/storyforge-training/preflight/r59/20261103:/input:ro
```

The file is then available as
`/input/R59_SFT_SHAPE_PREVIEW_PRIVATE.jsonl`. Do not use a source URL ending
in the JSONL filename while assuming the destination path itself is a regular
file: the observed mount exposed the destination as a directory and
`cp` failed with "omitting directory". Always run `test -f` against the
expected file path before processing.

A successful ChatGPT connector CPU submission does not imply that the RW
mount capability is restored. Keep these capability checks separate.

The follow-up SAFE token-length diagnostic (Job `6aea12470e0338d1bb7f5dec`)
measured all five preview rows without truncation at a diagnostic ceiling of
131072 tokens:

- within 16384: 3
- over 16384: 2
- median: 13660
- p95: 34263
- maximum: 114558

This confirms a real context-window issue in two of the five engineering-preview
rows. The diagnostic ceiling is measurement-only; it does not change the
accepted training budget. Do not truncate automatically or admit any row.
Design an explicit suffix/context-retention policy, preserve message ordering
and the final target, then rebuild a new preview and rerun the pinned CPU
collator.


The first ChatGPT-side R59 collator execution (Job
`6aea1084c78863f9c631e834`) resolved the pinned Hugging Face snapshot and
initialized the Qwen3.5-family template after adding the required vision
packages. A follow-up diagnostic (Job `6aea111fc78863f9c631e882`) reached
`ENCODE_COLLATE` and raised `MaxLengthError` at `max_length=16385`. This is a
data-length HOLD, not a submission, mount, or model-revision failure. Do not
enable truncation or reduce history automatically. Measure over-limit counts
and token lengths with an explicit SAFE diagnostic, then return to the
approved context-window design before rebuilding the preview. No admission or
training follows from this result.


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

