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
