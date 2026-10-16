# R50 tokenizer CPU Job — Git-native runner (2026-10-16)

The project source of truth for the **worker, launcher and tests is Git**. Private R50 prompts and candidate System text remain in the existing `adradar` Hugging Face **private Bucket**, not in Git. This uses previously staged private inputs; no ZIP handoff is needed.

## Incident and fix

- Job `6ad1d3a25ccb47ba0f7afcc4` exited 3 with `GPU_FLAVOR_FORBIDDEN`.
- Job `6ad1d585c6628814522599e4` exited 3 with `GPU_FLAVOR_FORBIDDEN: accelerator=cpu`.
- The original guard rejected the **actual CPU environment** `ACCELERATOR=cpu`. Worker now permits unset/empty, `none` or `cpu`, and rejects unknown/GPU values. The launcher fixes `--flavor cpu-basic`.
- No successful tokenizer result has been produced by these jobs. Do not report tokenizer PASS or final Held-out seal.

## Use existing HF Bucket stage (no ZIP)

Run from a local `sunxu/storyforge` checkout with the R50 audit branch checked out or the new commit fetched. The local `hf` CLI must already be authenticated with access to the private Bucket.

```bash
REPO="$HOME/workspace/storyforge"
git -C "$REPO" fetch origin audit/r49-r50-source-intake-20261015
git -C "$REPO" switch audit/r49-r50-source-intake-20261015
git -C "$REPO" pull --ff-only origin audit/r49-r50-source-intake-20261015
hf auth whoami

# Find existing stages created by the two earlier runs. Do not treat a Job ID as a stage key.
hf buckets ls 'hf://buckets/adradar/storyforge-training/preflight/v03-r50/cpu-tokenizer/'

# Run local guard tests before any staging. No remote execution.
bash "$REPO/scripts/test_r50_cpu_guard.sh" "$REPO/scripts/v03_r50_hf_cpu_worker.sh"

# Supply a *real existing* r50-token-YYYYMMDDTHHMMSSZ-xxxxxxxx key from that listing.
OLD_STAGE_KEY='r50-token-REPLACE-WITH-ACTUAL-STAGE-KEY'
bash "$REPO/scripts/v03_r50_hf_cpu_submit.sh" stage-from-bucket "$OLD_STAGE_KEY"
```

The last command copies only two pinned private input files from the old private stage, checks both frozen SHA256 values, stages the new Git-pinned preflight code and repaired worker under a **new key**, and prints `R50_STAGE_KEY=...`. It does **not** create a Job. Source prompts never enter Git.

After reviewing the new key, permissions, and billing impact, the owner may explicitly authorize a **new paid CPU job**:

```bash
NEW_STAGE_KEY='REPLACE_WITH_NEW_R50_STAGE_KEY'
STORYFORGE_ALLOW_PAID_CPU=YES STORYFORGE_R50_CPU_JOB_ONLY=YES \
  bash "$REPO/scripts/v03_r50_hf_cpu_submit.sh" submit "$NEW_STAGE_KEY"
```

The submit path compares the local worker SHA256 against the staged worker **before** `hf jobs run`, and rejects stale prior stages. CPU is `cpu-basic`, timeout `30m`, image `python:3.12-slim`; no GPU, model weights or inference. A CPU job may incur charges.

The future successful report (if any) remains private:
`hf://buckets/adradar/storyforge-training/preflight/v03-r50/cpu-tokenizer/<NEW_STAGE_KEY>/reports/R50_46_TOKENIZER.json`

Only a **sanitized aggregate summary** may enter `docs/evidence/` after validation; never commit the private 46-case JSONL, provenance, case-level token receipt, System plaintext, stage credentials or answers. Full semantic alias isolation and preregistration remain HOLD.

## 2026-10-16 CPU tokenizer dependency fix

The third CPU Job `6ad1e135c66288145225a9e3` reached the preflight but failed
with `ImportError: apply_chat_template requires jinja2 to be installed`.
`PyTorch was not found` is expected for the tokenizer-only container and was
not the fatal error. The worker now installs pinned `jinja2==3.1.6`, and executes
a Jinja2 rendering/import self-test before downloading the tokenizer. The local
guard checks that the dependency and remote self-test remain present.

**No Job is submitted by this commit.** Old HF stages still contain the
obsolete worker. Create a fresh stage by copying the existing private inputs
from the prior stage; the launcher verifies both input SHA256 hashes.

```bash
git fetch origin audit/r49-r50-source-intake-20261015
git switch audit/r49-r50-source-intake-20261015
git pull --ff-only origin audit/r49-r50-source-intake-20261015
bash scripts/test_r50_cpu_guard.sh

# Read a previously staged key from the existing private HF Bucket; stage only, no billable Job:
# OLD_STAGE_KEY must be the actual r50-token-... value from that listing.
bash scripts/v03_r50_hf_cpu_submit.sh stage-from-bucket \
  "$OLD_STAGE_KEY"
```

Record the **new** `R50_STAGE_KEY`. The owner may separately authorize a
new `cpu-basic` run using `STORYFORGE_ALLOW_PAID_CPU=YES` and
`STORYFORGE_R50_CPU_JOB_ONLY=YES` with `submit <NEW_KEY>`.
A CPU Job can incur charges. Do not reuse old stages or overwrite private
reports. No GPU, inference, or final Held-out seal is authorized.

## 2026-10-16: Qwen immutable revision metadata 404

CPU Job `6ad1e42dc66288145225ae0f` passed CPU guard and Jinja2,
then received `RevisionNotFoundError` at the explicit
`/api/models/Qwen/Qwen3.8-27B/revision/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0` API.
The public default model metadata and commit page still identify that same SHA.
This is **not** authorization to switch models, silently use a moving `main`
or ignore integrity checking.

The updated worker queries default model metadata and validates that the HEAD
SHA equals the frozen 40-hex revision; downloads only the published tokenizer
files via `revision=main` with `hf_hub_download`, and checks that **every**
returned cache path belongs to `snapshots/<frozen SHA>/`. It also verifies
the model HEAD again after downloading. If any check fails, it fails closed.

Before staging or submitting, run the network-only local probe without cost:

```bash
bash scripts/v03_r50_hf_cpu_submit.sh verify-model
bash scripts/test_r50_cpu_guard.sh
```

`submit` repeats the no-billing API probe and refuses an HF Job if it fails.
Old stages contain old worker bytes: create a **new** stage via
`stage-from-bucket <prior key>`, then review billing authorization for any
new `submit <new key>`. Neither the code commit nor the probe creates a
paid Job. A successful public SHA probe does not prove the remote tokenizer
download will succeed; actual HF CPU execution remains PENDING.

## 2026-10-16: Corrected root cause of HF revision mismatch

CPU Job `6ad1edc35ccb47ba0f7b1c00` reached the remote SHA guard but failed
`QWEN_MAIN_SHA_MISMATCH`. Its Worker contained the incorrect shortened
SHA `1d4bf0f2ff6012fd82039d0dd7c60c0` while the public model metadata, local free probe,
and immutable preflight code all used the correct full revision
`1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`.

**Erratum:** Earlier notes described an HF revision metadata API problem.
The 404 request also contained the same invalid SHA, so that diagnosis was
not established. The frozen model is **not changed**, and there is no reason
to switch to an unpinned model.

The Worker SHA is now corrected and the local `test_r50_cpu_guard.sh`
verifies the three SHA references (Worker, launcher, preflight), exact 40-hex
length, and rejection of the previous wrong SHA. This test is called by both
`stage-from-bucket` and `submit` before any paid job.

```bash
cd ~/workspace/storyforge
git fetch origin audit/r49-r50-source-intake-20261015
git switch audit/r49-r50-source-intake-20261015
git pull --ff-only
bash scripts/test_r50_cpu_guard.sh
bash scripts/v03_r50_hf_cpu_submit.sh verify-model

# Stage only, using the previous private HF inputs. No GPU or HF Job:
bash scripts/v03_r50_hf_cpu_submit.sh stage-from-bucket \
  "<PRIOR_R50_STAGE_KEY>"
```

Review the new `R50_STAGE_KEY` before separately approving any *paid* CPU
`submit`. Private narrative data stays in the HF Bucket; the five-job
incident audit in Git is text-free and preserves the original failure ID.
No final Held-out seal or quality promotion is authorized.
