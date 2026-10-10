# StoryForge v0.1 — Cross-Artifact Evidence Integrity Audit

**Audit date:** 2026-10-10  
**Technical result:** `V01_LOCAL_EVIDENCE_INTEGRITY_PASS__EXTERNAL_LIMITS_RETAINED`  
**Model disposition:** `ENGINEERING_PASS / QUALITY_PROMOTION_NOT_APPROVED`  
**Frozen historical tag:** `v0.1-evidence-frozen` → `d1186a731a81219f86eb81b89ac1440dd116e9f4` (**unchanged**).

This is a **post-freeze, read-only evidence-chain audit of committed v0.1 materials**, not a new training or inference experiment. The audit scripts and this report are on `main`, not in the original frozen tag.

## Executable evidence

- CPU standard-library audit: [`scripts/audit_v01_integrity.py`](../scripts/audit_v01_integrity.py).
- Pytest protection: [`tests/test_v01_integrity.py`](../tests/test_v01_integrity.py).
- The [CI workflow](../.github/workflows/ci.yml) executes the audit explicitly after Ruff and pytest.
- Machine-readable **actual CI output** (not a hand-authored synthetic success report): [`V01_CROSS_ARTIFACT_AUDIT_20261010.json`](evidence/V01_CROSS_ARTIFACT_AUDIT_20261010.json), sourced from [GitHub Actions run 38036181012](https://github.com/sunxu/storyforge/actions/runs/38036181012), job `114166961388`, at audited commit `f9159dabe927722d788321ad4aacc4ac1c3df0ef`.
- The CI run returned **72 passing tests**, Ruff PASS and the standalone evidence audit PASS. Future main changes rerun the same gate.

### Verified on committed bytes

| Area | Verified check | Result |
|---|---|---|
| Dataset v0.3 | SHA256 on `train.jsonl`, `validation.jsonl`, `test.jsonl`, `budget_report.json`, `token_report.json` matches the committed `SHA256SUMS.txt` | **5/5 PASS** |
| Dataset membership | Train 65, Validation 15, Test 20, 100 total; unique sample IDs and disjoint story IDs (15/2/2 stories) | **PASS** |
| Dataset context | Each sample has the last assistant Gold following a user turn | **PASS (structural)** |
| Token budget report | Reports 100/100 within 16,384; maximum reported length 16,259 | **PASS (report consistency)** |
| Accepted training config | Actual `configs/qwen38-27b-qlora-v0.1.yaml` SHA256 `8569a7b5502308ae4cd7d6778152ae7dca19303ee486632f6bd89ef6b099fbfa` equals the recorded accepted baseline hash | **PASS** |
| Training config references | Rank64, alpha128, last-round loss, gradient accumulation 8, 16,384 max length, train/validation v0.3 paths | **PASS** |
| Held-out Test | Canonical Dataset v0.3 Test prompt prefixes match frozen prompts, per-item SHA256, sample IDs, manifest lines and anonymous pairs/key | **20/20 PASS** |
| Frozen original evidence | Git Blob SHA-1 verified against the committed original bytes for each file in `evaluations/v0.1/git-blobs.json` | **20/20 PASS** |
| Held-out round 1 | 13 Base / 7 Adapter sample majority; 44/28/8 raw votes | **PASS** |
| Held-out round 2 | 10 Base / 10 Adapter sample majority; 34/25/1 raw votes | **PASS** |
| Checkpoint metadata | Original ten SHA256s in registry align with 10 read-only Bucket-listed sizes (5,603,977,212 bytes) | **PASS (record consistency)** |
| Validation 1536 | Original key + four archived scorecards replayed: Base 28, Adapter 30, TIE 2; 15 samples × 4 raters | **PASS** |
| Gold supplementary review | Six archived scorecards independently replayed: Gold vs Base 38/22, Gold vs Adapter 45/15; 120 rating entries on 20 original prompts | **PASS** |
| Frozen tag | GitHub remote tag still targets `d1186a731a81219f86eb81b89ac1440dd116e9f4` | **PASS (separate GitHub ref check)** |

**Important:** successful checksum verification of committed files does not imply proof about a file only stored remotely; that distinction is mandatory for acceptance.

### Evidence explicitly not re-executed

| Item | Status | Why this is not a new FAIL |
|---|---|---|
| HF A100 original training run and base-model revision | **Previously verified / not rerun** | Historical training logs show revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`. This Git CI does not recreate the remote run. |
| Remote HF training-input bytes | **PENDING independent remote rehash** | Committed Dataset Train/Validation hashes pass, but the remote A100 source files were not independently downloaded/compared in this audit. |
| Remote Checkpoint payload SHA256 | **REPORTED VERIFIED by prior CPU Job** | Job `6ac8be0e095c578089304f37` reported the 10 hashes and `STORYFORGE_SHA256_PASS`. CI checks the archived manifest, not the ~5.60GB payload. |
| Full original Validation 1536 HF JSONLs | **Prior user-ZIP verification / remote-only bytes** | The authentic user-supplied ZIP was previously validated 7/7 with 15/15 prompts, 30/30 model replies and 60/60 scored rows. Four larger original inference/prompt files remain in HF, with checksums recorded; the reconstructed model texts in Git are not substituted for raw HF bytes. |
| Gold-reference judge independence | **NOT VERIFIED** | Six scored files are available; the contributors' real-world identities and independence cannot be inferred from file submissions. |
| Tokenization and Gold-only gradient mask | **Historical engineering PASS / not rerun** | This script checks structural targets and saved token report; it does not load the tokenizer or ms-swift loss mask. |

### Historical wording that requires careful reading

- `configs/qwen38-27b-qlora-v0.1.yaml` contains an old header warning that rank64 GPU capacity was not yet verified. **Its immutable accepted SHA256 is correct**, and later HF capacity and Baseline jobs completed. Do **not** edit the old header in place merely for documentation clarity, as this would destroy configuration byte-level provenance.
- `docs/evidence/V01_GOLD_CANONICAL_RECONCILIATION_20261010.json` records `FORMAL_BLIND_RATING_PENDING` **at the time that older snapshot was written**. It was later superseded by the separate six-reviewer archive at `evaluations/v0.1/gold-reference/2026-10-10/`.
- `evaluations/v0.1/validation-1536/source_manifest.json` was prepared before the original HF ZIP was supplied. Read the later `hf-source/source_verification.json` for authenticated source claims, and retain its explicit `RAW_BYTES_REFERENCED_NOT_COMMITTED` qualification.
- Gold/Adapter and Gold/Base comparison panels are distinct groups on the same 20 prompts: do not infer a direct statistically proven Base-vs-Adapter outcome by subtracting the two panels.

## Final interpretation

**Committed evidence integrity: PASS. Historical engineering: PASS. Promotion of the v0.1 Adapter as production default: NOT APPROVED.**

Nothing from this audit modifies the frozen tag, historical reviewer files, historical model weights, Bucket contents or accepted training config. No HF CPU/GPU Job was launched.

The remaining remote-input/payload verification questions and reviewer-identity limitation are **transparent provenance limitations**, not silently treated as completed checks. The already-disclosed 20 held-out stories cannot be reused as an untouched generalization test.

## Reproduction

From repo root, Python 3.11+:

```bash
python3 scripts/audit_v01_integrity.py
python3 -m pytest -q tests/test_v01_integrity.py
```

Both are CPU-only and require no HF authentication or network access. The first emits structured JSON and exits nonzero if the committed evidence it checks becomes inconsistent.
