# StoryForge R50 — Three-ZIP Git-safe intake (2026-10-16)

Scope: `sunxu/storyforge`, branch `audit/r49-r50-source-intake-20261015`, Draft PR #2. Do not merge automatically.

## Exact uploaded archive identity

| Archive | ZIP SHA256 | ZIP entries |
|---|---|---:|
| `StoryForge_R50_46_Continue_20261016_PRIVATE_NO_GPU.zip` | `e2417394f440c2bb2af03168828919a40b97cb18bf7c57a0a7d983f1d4860755` | 8 |
| `StoryForge_R50_46_Content_Filtered_PRESEAL_PRIVATE_20261016.zip` | `b4da9164cb4d076cb99b4f790d23ce1896ff1cf33c7eb58788a961fd76cdb325` | 13 |
| `StoryForge_v02_R45_Phase1_Content_And_World_Closure_20261014.zip` | `da4b7718f1c1cbd0429553b684eeaf70f207fd2e41aae4e8fe0a52a11b647b9e` | 11 |

All 32 extracted entries were inspected. **Only the following seven original, non-narrative files are checked into ordinary Git** (all were compared against the extracted source by Git blob SHA):

1. Continue: `R50_46_FOLLOWUP_STATE_20261016.json` → `docs/evidence/V03_R50_46_FOLLOWUP_STATE_20261016.json`
2. Continue: `r50_full_r45_gate_from_frozen_git.py` → `scripts/v03_r50_full_r45_gate_from_frozen_git.py`
3. Continue: `r50_private_short_fragment_and_clusters.py` → `scripts/v03_r50_private_short_fragment_and_clusters.py`
4. PRESEAL: `R50_46_ADMISSION_STATUS_20261016.json` → `docs/evidence/V03_R50_46_ADMISSION_STATUS_20261016.json`
5. PRESEAL: `R50_CPU_TOKENIZER_PREFLIGHT_46.py` → `scripts/v03_r50_cpu_tokenizer_preflight_46.py`
6. PRESEAL: `build_r50_46.py` → `scripts/v03_r50_build_46_private.py`
7. R45: `verify_r45.py` → `scripts/private_archives/v02_r45_verify_original_package.py`

`.gitignore` is extended to warn/prevent unforced staging of known original private files; Git ignore is not a security boundary for forced adds or API writes.

## Intentionally NOT added to Git

25 extracted entries remain in their private original archives. In particular: R45 frozen Train49/Val15 raw JSONL, private decisions and witness quotations, R50 46-case narrative prompts, per-case provenance, per-case static input receipts, raw or near-raw AI review material and historical runtime reports. Do **not** use `git add -f` on these files. Keep byte-exact originals in restricted storage and record SHA256 separately. Other non-uploaded safe materials may be reviewed for a later ordinary Git commit; no claim is made that all 25 are inherently sensitive.

## Gate state and restrictions

- The owner explicitly excludes four previously HOLD/FAIL cases; 46 remain across five story worlds, with 364 historical messages.
- AI content quality PASS 46/46 is distinct from final admission.
- Complete five-story R45 exact-isolation execution: **HOLD / not run here**.
- Semantic alias/paraphrase isolation: **HOLD**.
- Actual pinned Qwen tokenizer preflight: **HOLD / not run here**.
- Four-arm inference-input contract: **DRAFT, not approved**.
- Final Held-out SHA256 seal: **NOT PERFORMED**.
- No GPU/HF job, model generation, answer-key storage, prior R45–R48 mutation, or PR merge in this intake.

Note: The archived R45 verifier expects the complete original extracted R45 package beside the script; the standalone checked-in copy is a byte-identical archive of the tool, not a claim it can pass without the private inputs.

**Result:** `THREE_ARCHIVES_INSPECTED__SEVEN_SAFE_FILES_COMMITTED__PRIVATE_DATA_EXCLUDED__FULL_ADMISSION_HOLD`.
