# StoryForge v0.2 — R18 HF CPU no-training preflight

**Training admission: PENDING_NOT_APPROVED.** Do not run `swift sft`.

Historical references in this repository: `docs/HF_JOBS.md`, `docs/HF_RUN_REGISTRY.md`. HF namespace: `adradar`. Private Bucket: `hf://buckets/adradar/storyforge-training`. Diagnostic model revision (from v0.1): `Qwen/Qwen3.8-27B@1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`. No production v0.2 model revision has been approved.

## On your Mac

From the project checkout, download the original **R17 ZIP from this ChatGPT conversation** to `~/Downloads/`. The ZIP is 12 MB and contains original confidential story source; **DO NOT commit it to GitHub**.

```bash
cd /path/to/storyforge
git pull --ff-only origin main
python3 -m pip install -U huggingface_hub
hf auth login
# Hash-verified sync to the existing PRIVATE bucket. No paid Job starts.
bash scripts/v02_r18_submit_hf.sh \
  "$HOME/Downloads/StoryForge_v02_R17_Runtime_And_Label_Contract_20261013.zip" sync
```

After verifying private bucket contents, **explicitly choose a paid CPU diagnostic job**:

```bash
STORYFORGE_ALLOW_PAID_CPU=YES bash scripts/v02_r18_submit_hf.sh \
  "$HOME/Downloads/StoryForge_v02_R17_Runtime_And_Label_Contract_20261013.zip" submit
```

This invokes HF Jobs with `--flavor cpu-upgrade --timeout 90m`, installing the project's recorded historical `ms-swift==4.5.3` and `transformers==5.16.1`. Dependency compatibility and CPU-only get_processor behavior **are not yet remotely proven**; errors must stay BLOCKED. No optimizer, no model weights, no training.

For token counts only (cheaper environment / no ms-swift):

```bash
STORYFORGE_R18_STAGE=token STORYFORGE_ALLOW_PAID_CPU=YES \
  bash scripts/v02_r18_submit_hf.sh \
  "$HOME/Downloads/StoryForge_v02_R17_Runtime_And_Label_Contract_20261013.zip" submit
```

The launcher prints `R18_RUN_KEY=r18-...` and `R18_RESULT_PREFIX=...` before starting the Job. Save the **RUN_KEY**, which is distinct from the Hugging Face **JOB_ID**. HF executes the mounted worker script directly rather than attempting to run a long command string. Retrieve the Job ID printed by `hf jobs run`:

```bash
hf jobs logs adradar/JOB_ID
hf buckets ls hf://buckets/adradar/storyforge-training/preflight/v02-r18/results/R18_RUN_KEY/
hf buckets cp \
  hf://buckets/adradar/storyforge-training/preflight/v02-r18/results/R18_RUN_KEY/r18_actual_no_train_report.json \
  ./r18_actual_no_train_report.json
```

If installation fails before the Python auditor starts, no JSON report is guaranteed: read the HF Job logs. `sync` sends the worker script plus the two Python audit files; no GPU or training process is launched.

## Guarantees and limitations

- R17 ZIP SHA256 pinned: `ba42ad7568ce0ca3ab8b3d218397006b430affc9f1b2f74b7ea4392e5103eab3`.
- R15 diagnostic queue SHA256 pinned: `27d63ccc7652e41403d9cb4add58c0aa7d2925282d4bd8605bff4d7564133ac7`.
- R07 frozen preview SHA256 pinned: `21255ffaf3460721bfbd89fb448e4cf5bcf53e98d3eec76585a7817e8bafd210`.
- Exactly **40** first-lane samples only. The other 155 quality candidates remain excluded from model diagnostics.
- The script checks actual Hugging Face tokenizer counts and, in `both` mode, calls the project's previously audited `hf_label_mask_audit.audit_row` against the actual installed ms-swift template before checking collator labels. If a real collator cannot be obtained, it fails closed.
- `TOKENIZER_DIAGNOSTIC_ONLY` and `COLLATOR_INTERNAL_CONSISTENCY_ONLY` mean exactly that: neither grants training approval.
- Still BLOCKED: content/age safety dispositions; the R14 HOLD and truncated-window routes; new held-out stories; v0.1 complete story/world UUID overlap; approved train/validation/test splits; formal human approval.
- The Git repository contains **scripts and documentation only**. The nested R17 ZIP is sent solely to the user's existing private HF Bucket.
