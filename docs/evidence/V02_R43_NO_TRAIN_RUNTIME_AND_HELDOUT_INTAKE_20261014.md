# StoryForge v0.2 — R43 operational preflight & independent heldout intake

Date: 2026-10-14. **Artifact/tooling milestone only. R42 staged 56 Train / 16 Validation are unchanged. No model train authorization.**

## Done on local CPU
- Re-ran R42 exact-copy data static gate: 56 Train (6 story UUIDs), 16 Validation (3 story UUIDs), all 72 target SHA256 matches and target-only static loss declarations. Train SHA256 `d94eaf861d7d86951c1ab0e60dbb38fb006998e9a6a035c19c544ba4d44862ee`; validation SHA256 `87eb9f6a4b552c681edbfe3977af07c3a205234ad76f6de42810aa749a8fb47a`.
- Created `r43_gate.py` for reproducible version-locked offline stages; recreated ZIP SHA256SUMS; package verifier PASS. GPU authorization tamper rejected.
- Built `r43_hf_actual_collator_no_train.py`: requires actual installed `ms-swift==4.5.3`, `transformers==5.16.1`, pinned Qwen tokenizer revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`, and existing repo `scripts/hf_label_mask_audit.py`. Tests every staged row with actual template/last-round semantics, target-off counterfactual, token budget, actual batch collator. Never invokes training. **This local environment lacks ms-swift so actual runtime status is BLOCKED, not PASS.**
- Built a fail-closed independent heldout intake check: 40–60 externally authored prompts from >=4 new worlds, no assistant target responses, author/source rights and non-exposure declarations, current and v0.1 exact world-UUID exclusions, 40-character overlap probes, output SHA256 sealing. A single example/empty template is correctly rejected. No independent item has been supplied.
- No private training target texts or prompt source contents added to ordinary Git.

## Required from the project owner (only two actionable items)
1. Arrange an external author/assessor who has not read StoryForge Gold/training or prior test prompts to supply **40–60 new heldout prompt records across >=4 unrelated new story worlds**. Prompt records contain the story/world setup, optional past dialogue, current user input, and human independence + internal evaluation rights declarations. **No model outputs or answer keys yet**.
2. Run the no-training preflight on an available HF CPU environment with the pinned libraries and share its `R43_HF_RUNTIME_REPORT_PRIVATE.json` (no API keys or GPU job required). Full detailed instructions and scripts are in the private ZIP.

Training story use rights and age legality were previously accepted as project-owner declarations; do not request documentary evidence again.

## Exact private artifact
`StoryForge_v02_R43_Preflight_And_Heldout_Intake_20261014.zip` SHA256 `6728ffc81f98e1f5b8db098ec40a09442ef7e8b77e888e5f535fd9bbfe21412a`.

**Checkpoint:** 72 static stage rows PASS; actual runtime collator BLOCKED until HF report; 0 new independent heldout; 0 final Train/Validation/Test approvals; no GPU authorized/launched. Source-history semantics and complete hidden alias/world graph remain scope-limited, not falsely certified.
