# StoryForge v0.2 — R27 fast-track provisional dataset and real HF re-audit

**Status: `PENDING_NOT_APPROVED`. No formal training job started; immutable 195 Gold remain untouched.**

## New concrete artifact

A private ChatGPT handoff ZIP (`StoryForge_v02_R27_Training_Readiness_20261013.zip`) was produced with SHA256 `1f6d41b0bfc9c4382c55debc82770a3cad7c9cd38c99026213cc624bc418c286` and strict portable `verify_r27.py`. The confidential `output/r27_private_candidate_117_NOT_APPROVED.jsonl` is **not stored in Git**; SHA256 `cdecc311f05e2c700f1038f3afca09c889ff681d4ef55dc18dc7426c9d14a92a`. The package includes portable input builder, 195-row route ledger, group-level split proposal, and HF CPU actual tokenizer/ms-swift `last_round` check with fail-closed guards.

From 195 original curator-quality candidates:
- 38 prior HOLD quarantined.
- 18 War & Blood age/content-special samples quarantined.
- 19 **additional** candidates sharing a v0.1 historical Train story UUID quarantined (21 exact UUID overlaps, 2 already in HOLD).
- 2 original message revision-history cases quarantined.
- 1 newly identified empty historical User-turn body quarantined (`s09-gold-r03-t00222`).
- **117 provisional derived diagnostic candidates** remain: 40 original visible windows; 77 source-recovered predecessor-pair windows, without any rewrite of Gold target text.
- 11 independent *story UUID groups*. Only a **proposal** of 96 Train + 21 Validation in disjoint UUID groups; no fresh unexposed held-out or shared-world alias clearance.

The R27 input uses an explicit **new generic synthetic System prompt** and source-visible history; it is NOT represented as the original model request, and no as-of story-card facts are injected.

## Verification boundary

- Read-only checks: frozen target SHA256, declared final-target supervision, messages' roles, R26 recovered pair SHA256, R15 routing, R20 historical story-UUID membership and R21 40-row bounded review identity.
- `R27_DRAFT_INTEGRITY_AND_FAIL_CLOSED_GATE_PASS_ONLY`: independently unzipped, verified 117 draft targets and 195 routes; intentional input tampering failed.
- Local failure test of the HF CPU script with wrong expected input hash exited **2 / BLOCKED**.
- **Actual HF full-input tokenizer and collator audit for these 117 has NOT been run**. R18 40/40 report does not cover the 77 modified prefixes.

## Fastest owner-side next step (paid HF CPU, not SFT)

Download and unzip the *private* R27 ZIP to the Mac. Run from the project checkout, where `scripts/hf_label_mask_audit.py` already exists:

```bash
STORYFORGE_REPO="$PWD" STORYFORGE_ALLOW_PAID_CPU=YES bash "$HOME/Downloads/StoryForge_v02_R27_Training_Readiness_20261013/r27_hf_submit.sh" submit
```

The launcher syncs only to the user's existing private `hf://buckets/adradar/storyforge-training/preflight/v02-r27` and requests `cpu-upgrade` for an actual Qwen pinned tokenizer and `ms-swift==4.5.3` `last_round` internal collator audit, **no optimizer steps**. Result: `.../results/R27_RUN_KEY/r27_hf_final_input_report.json`.

**Still blocking official full GPU SFT:** final contextual content/age authorization, effective-as-of card provenance or approved new no-card derivative contract, linked-world alias isolation, genuinely unseen heldout, approved fixed split, final-input HF Token and label audit, and explicit final release gate. The model-side Hugging Face account is not connected to the assistant's runtime; no paid job could be started directly here.
