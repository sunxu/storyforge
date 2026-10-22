# StoryForge R50 CPU46 — successful HF CPU-only Owner intake (count-only)

Date: 2026-10-23 (Asia/Singapore). Evidence type: Owner uploaded *count-only* intake receipt; its local file bytes were SHA256 checked in this conversation. No private R50 prompts, raw HF Job results, or private stdout/stderr were received.

- HF Organization: `adradar`; Job ID `6ada3f1d925af0e27d4f569f`; run key `r50-cpu46-20261022T164410Z-305591`.
- Owner terminal: `R50_CPU46_OWNER_INTAKE_REPORT_HASHES_PASS__DRAFT_ONLY__NOT_FINAL_SEAL`.
- Submitted Owner intake JSON SHA256: `9b922c53cdafab11bd523e9c70f71a66a45d631da2b033487f2320b4150fe781` (1080 bytes).
- Intake schema `storyforge-r50-hf-cpu46-local-intake-v2`; source count `46`; `original_script_exit_0_and_json_generated=true`; `training_run=false`; `model_inference_run=false`; `paid_gpu_run=false`.
- Submitted intake's pinned `stage_manifest_sha256=b91455bbed7cf15d7defc430631ecfb4a3f9451ba8188a2dd0ce1c0fb5876540`.
- Submitted intake's pinned `remote_receipt_sha256=7db2546176621478899bf64ae9d4ade127b216de0e64edcb6c8efa618ca94f5b`.
- Submitted intake's pinned `remote_private_report_sha256=56aeac340ac1c0be1d0000314bcbdc72abd2f59582d643eee9e50698529f748e`.
- Submitted intake's pinned `remote_private_log_sha256=1d24451e78124cea45b24bbc085cf0eccbfbf4a62b9db919f8f826047934551b`.
- Runtime: Transformers `5.16.1`; Qwen tokenizer revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`.

**Provenance distinction:** The submitted JSON itself was checked against its own bytes in the current environment and the status was cross-read against the Owner's terminal output. Private remote report/log bytes remain solely in the Owner Mac and protected HF Bucket; their SHA256s were **reported by the Owner's original local verifier**, not independently recomputed from the protected files here.

**Decision:** Accept the limited `R50_CPU46_OWNER_INTAKE_REPORT_HASHES_PASS__DRAFT_ONLY__NOT_FINAL_SEAL` at Owner-receipt level. This is **not** a quality, content, sealed Held-out, 46/46 token-budget or double-user role-contract pass. The 46-row private Tokenizer report still needs safe offline length/role statistics. Current proposed context 16384 and 1536 output reservation imply a *draft* 14848 input budget; not yet an accepted four-arm evaluation contract. Retain `official_heldout_admitted=0`, `final_seal=false`, `semantic_world_isolation=HOLD`, and no GPU/inference/training or R54 promotion.
