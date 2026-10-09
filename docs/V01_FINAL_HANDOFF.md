# StoryForge v0.1 — Final Handoff

**Date:** 2026-10-09  
**Status:** ENGINEERING_PASS / HELDOUT_REVIEW_COMPLETE / QUALITY_PROMOTION_NOT_APPROVED  
**Immutable historical checkpoint:** [`v0.1-evidence-frozen`](https://github.com/sunxu/storyforge/tree/v0.1-evidence-frozen), commit `d1186a731a81219f86eb81b89ac1440dd116e9f4`.

This handoff is added to `main` **after** freezing v0.1 evidence and does not change the tag. Detailed primary evidence is in [`evaluations/v0.1/`](../evaluations/v0.1/README.md). HF Job and artifact references are indexed in [`HF_RUN_REGISTRY.md`](HF_RUN_REGISTRY.md).

## Delivered

- Dataset v0.3: 100 selected Gold responses, story-level split 65 train / 15 validation / 20 held-out test.
- Training: `Qwen/Qwen3.8-27B` with rank64 QLoRA 4-bit NF4 BF16 and last-round-only Gold loss supervision; 1 epoch, 9 optimizer steps, adapter checkpoint-9.
- Engineering: A100 80GB smoke, rank64 capacity check, official baseline train, checkpoint reload, validation and test paired inference all accepted.
- Held-out review: 20 story-isolated prompts; two reviewer rounds, documented arbitrations, source-key-verified unblinding.
- Source evidence and answer mapping archived publicly by user authorization in the single StoryForge repository.

## Frozen assessment

| Metric | Review round 1 | Review round 2 |
|---|---:|---:|
| Base sample wins | 13 | 10 |
| Adapter sample wins | 7 | 10 |
| Base raw preference votes | 44 | 34 |
| Adapter raw preference votes | 28 | 25 |
| Raw ties | 8 | 1 |

The same 20 prompts were rated twice; these **are not 40 independent test items**. First-round q reasons include known alignment issues. Second-round ceh 018/019 score-area transposition was corrected; both original and fixed versions are retained. The similarly named `ch.csv` uploads from the two rounds are distinct records.

The adapter did **not** establish reliable aggregate quality improvement over Base; production promotion is **not approved**. Second-round results are sample-level 10:10, with a small aggregate Base preference and scores advantage. Human review uncertainty and small sample size limit general conclusions.

## Next phase: v0.2 / Dataset v0.4

1. Define failure taxonomy and Gold selection rubric (story facts, user agency, character arc, prose quality, interactive progression).
2. Acquire **new, story-isolated** examples for training, validation, and a genuinely unseen future held-out test. Do not recycle the disclosed v0.1 test as untouched v0.2 acceptance evidence.
3. Audit Gold quality and supervision mask before billable experimentation.
4. Run CPU-side checks and cheap ablations first; authorize any HF GPU job separately.
5. Freeze inference protocol and acceptance gates **before** seeing new held-out results; compare Base against any candidate adapter.

## Outstanding reproducibility details (non-blocking)

- Exact base model snapshot revision: VERIFIED — `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0` from the original A100 baseline Job log.
- Saved `adapter_model.safetensors` and nine accompanying checkpoint file SHA256 values: REPORTED VERIFIED by completed HF CPU Job `6ac8be0e095c578089304f37` (`STORYFORGE_SHA256_PASS`). These hashes are archived in `docs/HF_RUN_REGISTRY.md`; repository CI did not independently rehash the 5.60 GB payload.
- Exact per-file checkpoint byte sizes: PENDING. Collect authenticated **metadata only**, without another Job, using `scripts/hf_checkpoint_size_manifest.py`.
- Complete remote Job manifest/log integrity checks: PARTIAL, see HF run registry.

These fields should be populated from existing artifacts if available, not invented. Nothing here requests a new GPU run.

## Operational safety

- Do not move, delete or rewrite the `v0.1-evidence-frozen` tag.
- Keep the frozen evaluation source files immutable, including original and corrected reviewer versions.
- Public research materials are allowed by the project owner, but never commit live credentials or private keys.
- Model weights and large checkpoint artifacts remain in the Hugging Face Bucket.
