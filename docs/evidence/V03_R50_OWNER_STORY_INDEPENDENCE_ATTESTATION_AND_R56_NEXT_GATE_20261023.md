# StoryForge R50 — Owner story-independence attestation and R56 decision route

**Recorded:** 2026-10-23, Asia/Singapore. **Classification:** Owner/author testimony, not an independently verified content review. No private story/prompt/answer material accessed, included, or committed.

## Owner's explicit statement

The Owner states in the current conversation: **“故事是独立的，没有关联的。”** In this context the response addresses the repeated question of whether StoryForge story worlds share characters, organizations, settings, unique events, or continuing plots. Record this as `OWNER_ATTESTS_STORY_INDEPENDENCE`. The Owner has not provided fresh source-message/card snapshots here. The authorial statement is material evidence of intended narrative independence; it is **not** evidence that train/test material has never been exposed, that historical model-input rules match the cards, or that previously reported positive semantic graph edges are disproven. Keep any conflicting earlier documented 04/07 edge as a separate evidence discrepancy, not silently deleted.

**Workflow decision:** stop repeatedly requesting the same world-independence assertion or rerunning identical lexical/AI reviews without new evidence. Proceed with independent-test *design and preregistration preparation*. Explicitly identify Owner-attested versus independently validated gates in any final evaluation report. Protected final-test admission still requires an authorized release decision.

## Established R50 input engineering

- Frozen PRESEAL 46 candidates; SHA256 `109642a6c0e27895ae83274bec79ec9f53d922e407ca435431acf3f31a31e1f2`; five R50 world groups with cases 9/10/9/8/10; historical messages 364; 12 trailing-User histories.
- Actual Qwen tokenizer pinned `Qwen/Qwen3.8-27B@1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`, transformers `5.16.1`, latest protected HF CPU Job `6ada3f1d925af0e27d4f569f`.
- 46/46 fit **draft** context 16,384 less reserved output 1,536 (input budget 14,848), input max 8,757, and 12/12 trailing User message sequences preserved/encoded. Owner count-only receipts archived in `V03_R50_CPU46_OWNER_TOKEN_LENGTH_SAFE_AGGREGATE_20261023.md` and `V03_R50_ROLE12_OWNER_INTAKE_SAFE_20261023.md`.
- Draft input construction preserves original histories and two adjacent User turns **without merging or truncation**. Actual model-arm deployed input parity and the Owner's final interpretation policy remain not approved.

## Model-readiness reality (do NOT call promoted)

- Base: Qwen frozen revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`, no adapter.
- v0.1: prior checkpoint-9 adapter SHA256 `621d7328056758607c9d7797282ae4d5803cdb1727dab6b40a321ee959dd2478`.
- v0.2 R46: reported adapter SHA256 `bec4ba74d858db3ff117d581478ef9cac41b1ecc7ea2a67523f6db1096addf2b`.
- v0.3-A R54: 16-step GPU training completed; Owner GPU engineering report already accepted, reported adapter SHA256 `121ec8f70e66089c7c891a7052c6085de93824776aaa9a25295f612b269b60c0` at `output/v0-20261021-162418/checkpoint-16`, Job `6ad8e60f5275124786e27d21`. R54 is **NOT PROMOTED**.
- R55 20 old/reused **development** prompts from 2 exposed worlds: v0.3 majority case preference **12/20** over v0.2, but **all six dimensions** averaged lower on v0.3 (overall 3.2750 vs 3.3972) and serious player-agency reviewer-case flags were 9 vs 7 (not adjudicated distinct cases). Therefore R55 is **mixed and inconclusive**; no evidence of robust quality improvement or authorization to test on protected R50.

## Next two no-new-job actions (recommended sequence)

1. **R55 candidate GO / NO-GO based only on existing unsealed development outputs:** inspect already frozen 20 development-case blinded replies for failure taxonomy; independent reviewer adjudicates severe agency flags and key six-domain regressions *without new R50 access or new model inference*. Decide if this exact v0.3 adapter is ready to spend the one-time R50 holdout, or needs revision in the *development lane* first. No v0.3 promotion claim from 12/20.
2. **Prepare R49/R56 four-arm evaluation preregistration for Owner signoff, without touching private R50 prompts:** exact model/adapter SHA, shared frozen System+world+rules, 364 histories preserved, 12 consecutive User pairs retained, thinking disabled, no truncation, output reserve / max generation 1536, identical runtime tokenizer/template pins for Base/v0.1/v0.2/v0.3, frozen deterministic generation args and EOS policy, R50 identity custody and unblinding, predeclared 3 independent blind reviewers, separate four-way and direct v0.3-v0.2 pairwise, six-domain scoring and agency/forbidden-text adjudication, cluster-by-world statistics, formal GO/NO-GO thresholds. **Approval is required** before the one-time private seal / inference.

**Hard controls:** no reusing R47/R48/R55 as fresh R50, no R50 private body/mapping in Git or developer channel, no GPU/paid Jobs without explicit authorization, no automatically sealing or promoting data/models, no R50 target-leakage. Existing R50 formal admission `0`, final seal `false` remain until independent final release.

**Status:** `OWNER_ATTESTED_WORLDS_INDEPENDENT__R50_TOKEN_ROLE_DRAFT_PASS__R55_CANDIDATE_GO_NO_GO_PENDING__R56_PREREGISTRATION_PENDING__NO_FINAL_SEAL`.
