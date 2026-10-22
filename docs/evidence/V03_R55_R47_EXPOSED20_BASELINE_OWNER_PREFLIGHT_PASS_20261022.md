# StoryForge R55 — R47 exposed-20 historical R46 baseline source check

Date: 2026-10-22 (Asia/Singapore).

**Owner-reported status:** `R55_R47_EXPOSED_20_BASELINE_SOURCE_VERIFIED__NO_GPU__R50_SEALED`.

The Owner executed the `r55_dev_source_preflight.py` historical-source validation for the frozen 20 previously exposed R47 prompts against the existing R46 `v02-results.jsonl` and `R47_PRIVATE_RUN_REPORT.json`, then returned exactly the expected PASS terminal marker above. This follows an earlier Owner Mac `34/34` Python offline unit-test PASS.

### Identity and scope

- Previously exposed R47/R48 source: **one set of 20 prompts** across two prior worlds, NOT 40 new independent prompts. These results are development regression only.
- Frozen R46 adapter SHA256: `bec4ba74d858db3ff117d581478ef9cac41b1ecc7ea2a67523f6db1096addf2b`.
- Existing R47 inference run: `r47-20261014T091647Z-637890`; this step reuses saved results and is not a new inference.
- R54 candidate training run: `r54-v2-20261021T161818Z-507469`, Step 16 adapter SHA256 `121ec8f70e66089c7c891a7052c6085de93824776aaa9a25295f612b269b60c0`.
- Frozen R55 two-arm contract: `configs/v03_r55_exposed20_pairwise_dev_contract.json`.
- Planned inference: `Qwen/Qwen3.8-27B` revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`, `temperature=0`, `seed=42`, `data_seed=42`, `max_new_tokens=1536`, shuffle false, exact same prompt history.
- Three independent blinded pairwise reviewers score the **same 20 cases**, with per-case preference, explicit hard-rule failures, and severe player-agency problems. Reviews must freeze before coordinator-only unblind.

### Evidence limitation

Only the PASS terminal marker was furnished in this interaction. The underlying generated `R55_OLD_R47_SOURCE_PREFLIGHT_SAFE.json`, R47 private run report and raw historical response JSONL were **not uploaded to this interaction for fresh independent rehash**. Status therefore means Owner-returned source preflight PASS; it does not imply a separate second-party rehash, a fresh model-generation run, or 20 completed R54 outputs.

### Next steps

1. Preserve the Owner-generated safe R47 source preflight receipt; no R46 GPU rerun.
2. Prepare a **new, separately authorized, single R54 Step 16 GPU inference** for the same 20 exposed prompts only; it must generate a pinned report and align all 20 prompts, responses, model revision, and adapter SHA256 before evaluation.
3. Produce randomized LEFT/RIGHT blind pairwise review sheets, conduct three independent reviews, freeze before unblind.
4. **No R50 access, no model promotion, no permission for paid GPU training/retry.**

**Current state:** `R55_HISTORICAL_R46_EXPOSED20_OWNER_SOURCE_PASS__R54_DEV_INFERENCE_NOT_AUTHORIZED__R50_SEALED`.
