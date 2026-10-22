# StoryForge R55 — exposed-20 pairwise development evaluation preparation

Date: 2026-10-22 (Asia/Singapore).

**Current state:** `R55_EXPOSED_20_CPU_EVALUATION_GATES_PREPARED__NO_NEW_GPU__NO_R50__NOT_PROMOTED`.

## Frozen retrospective scope

R47 and R48 covered the **same 20 previously exposed v0.1 Test prompts**, not 40 independent examples. The earlier R47 report covered Base, v0.1 and R46 v0.2; R48 reused those exact questions with Gold for a four-arm retrospective assessment. There are only 2 exposed story worlds in this test. R55 is an explicitly **development-only** direct pairwise comparison, **R46 v0.2 vs R54 v0.3**, not a fresh heldout and not grounds for model promotion.

Official unchanged Git blobs:
- `evaluations/v0.1/test/prompts.jsonl`: Git blob SHA1 `ac301a61d4130369a83dc67ac02aa2d8dda9e82b`.
- `evaluations/v0.1/test/manifest.json`: Git blob SHA1 `f4e39196c6aa0a87b095d7de5cae4acd8b2fca63`.

Frozen source:
- R46 adapter checkpoint-7 SHA256 `bec4ba74d858db3ff117d581478ef9cac41b1ecc7ea2a67523f6db1096addf2b`.
- R54 owner-accepted checkpoint-16 SHA256 `121ec8f70e66089c7c891a7052c6085de93824776aaa9a25295f612b269b60c0`.
- Qwen/Qwen3.8-27B revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`.
- Prior R47 existing 20 R46 replies: private HF `evaluation-runs/v02-r47/r47-20261014T091647Z-637890/v02-results.jsonl`, checked against its matching private R47 report. **No R46 inference rerun necessary.**
- Pinned proposed R54 inference on unchanged 20 prompts: `temperature=0`, `seed=42`, `data_seed=42`, `max_new_tokens=1536`, `val_dataset_shuffle=false`. **No such 20-response R54 run authorized or performed by this preparation.** The one old R54 post-SFT validation reload sample is **not** the 20-case development inference.

## Executable CPU-only deliverable, actually tested

A portable package `StoryForge_R55_Exposed20_Development_Eval_NoGPU_Preparation_20261022.zip` was created and verified. SHA256:
`358bcf15a0129fc854eb7973a70c8d75ca0d85ed0f9c808fbce09689ed6f154f`.

It contains:
- `docs/R55_DEV_EVAL_CONTRACT.json` SHA256 `bd6868ba846360054ac753d53cd3081a33acb126b39727ea516eb58c149082b3`.
- `docs/README_R55_CN.md` with no-cost historical data retrieval/preflight and later review steps.
- `scripts/r55_dev_source_preflight.py` SHA256 `952317ae1babbc4dab729a25bb9eac81ca37e1ca8854cfc2c3f9c94145b637f6`.
- `scripts/r55_dev_pairwise.py` SHA256 `1e26ec41cdf05125367bade5073390c51db74356fa2c51ce9590af88356a4d40`.
- `scripts/r55_dev_review_freeze.py` SHA256 `008b0b503ba6ae03ea5fd6f363926b22f93595efcbc90decaac839560bdc6cb8`.
- Three complementary Python unit-test files and `SHA256SUMS.json`.

**Actual execution: 34/34 Python unittest cases PASS**, and ZIP CRC + every packaged member SHA256 PASS. All tests use **synthetic test prompts and synthetic responses**, never sealed R50. The command-line scripts require the exact official old Git prompt/manifest blob SHA1, existing R47 R46 response/report hash and model identities; when a future R54 20-response result exists, they also require a pinned real inference report with exact R54 Adapter SHA, model revision, prompt/manifest hashes and inference arguments. A source-only preflight can be run immediately with no GPU.

The evaluator produces separately blinded randomized LEFT/RIGHT answers, three reviewer CSVs, a mode-0600 coordinator key, 6×2 quality scores per item, LEFT/RIGHT/TIE preference, severe player-agency and explicit banned-phrase flags. Scored CSVs must match the pristine original prompt and answer text. Three full reviews are hashed/frozen **before** the optional coordinator-only unblind. Development majority wins and potential 1/1/1 splits are counted per **case**, not treating 60 individual reviews as 60 independent questions. It never reads R50 or initiates inference/training.

Safe receipt `R55_DEV20_NoGPU_Preparation_Safe_Receipt_20261022.json` SHA256 `2eb82edbdc2692372275968c88d15f6fc83438b179e0c3ee6c235abdbb9af000`.

## Restrictions and next gate

The ZIP contains **code, tests, source pointers, SHA digests and public-safe contracts only**, with no story prose, old raw 20 prompts, model outputs, model weights, secrets or sealed R50 content. The full Python source and tests are in this conversation's downloadable ZIP; **they have not been individually committed into the repository in this action**. Their presence in a GitHub repository must not be assumed from this audit document.

Next free action: on Owner Mac, use previously downloaded private R47 files and the original repo `evaluations/v0.1/test` prompt/manifest to execute the package's source preflight. Next paid step: **a separately authorized 20-prompt R54 development inference** (not included in prior R54 SFT approval), with exact Adapter and prompt SHA validation. No GPU job, model training, quality promotion or R50 opening was authorized or performed by R55 preparation.
