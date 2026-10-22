# StoryForge R50 CPU46 — frozen-revision tokenizer path root cause and fix

Date: 2026-10-22. Source: Owner's locally inspected private stderr of HF CPU Job `6ada2b71c191903149a728b1`.

**Confirmed root cause:** `R50_TOKENIZER_PREFLIGHT_HOLD: ValueError: tokenizer snapshot path must include frozen model revision directory`. The first Worker downloaded tokenizer files to a *flat* `/tmp/storyforge-r50-qwen-tokenizer`, while the original private preflight rejects snapshot paths without the pinned model revision as a directory component. Public tokenizer download finished; the original preflight exited 1 **before** the 46-case tokenizer report could be produced.

**Versioned code fix:** make `snapshot_download(repo_id=MODEL, revision=REV, local_dir='/tmp/storyforge-r50-qwen-tokenizer/snapshots/<REV>')` and fail closed if the returned path is not this exact pinned revision directory. Original private R50 preflight, 46 candidate input, frozen System, Qwen revision, and CPU-only runtime are unchanged.

**Synthetic tests:** 18/18 PASS, including rejecting a tokenizer snapshot directory lacking the revision. No new real HF Job and no proof of 46/46 successful runtime tokenization.

**Governance:** Old failed `RUN_KEY=r50-cpu46-20261022T151846Z-950025` is consumed and immutable. Never re-submit it or modify its staged SHA256 manifest. To test changed code, create a **new** `sync` stage, recheck its frozen bytes, and execute `submit` only with explicit separate Owner approval of another billable CPU Job. Do not send R50 protected prompts into the training Bucket; use `adradar/storyforge-r50-audit` with verified restricted access.

**State:** `R50_CPU46_TOKENIZER_REVISION_PATH_ROOT_CAUSE_FIXED_IN_CODE__HF_RUNTIME_NOT_RERUN__NO_FINAL_SEAL`. Official heldout admitted 0. Semantic world isolation HOLD, input contract still DRAFT, no model inference/GPU/training/promotion.
