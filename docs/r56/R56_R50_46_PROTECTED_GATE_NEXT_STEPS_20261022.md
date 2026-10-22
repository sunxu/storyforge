# StoryForge R56 — R50 46-case protected gate: latest evidence and exact next CPU action

**Date:** 2026-10-22. **Purpose:** preserve sealed R50 and move from already completed source replay / AI-only content triage to the *remaining* independent-test admission gates. This document contains no R50 candidate text, mapping, answers, private case identifiers or character names.

## Authority / temporal precedence

1. **2026-10-15 main intake:** five candidate-world sources located, but full source replay and test item intake were still pending.
2. **2026-10-16 GitHub audit-branch source receipt** `docs/evidence/V03_R50_REAL_SOURCE_REPLAY_20261016.json`, branch `audit/r49-r50-source-intake-20261015`: original **50/50** cases, **392/392** frozen history references, **50/50** card *effective intervals* match frozen source. This does **not** prove target-time card fact validity, semantic world isolation or sealed admission.
3. **2026-10-16 Owner-private coordinator/follow-up audit reports:** original 50 immutable; Owner explicitly excluded **4**; derived **46-case PRESEAL** set, **364** history messages across **5** candidate worlds with **9/10/9/8/10** cases, AI-only content check PASS for 46. No user prompt or source text from these sealed materials was inspected by this decision.
4. The original **R45 49 Train / 15 Validation byte SHA** is *reported PASS* in later private audit. A **visible-field** normalized 40- and 64-character lexical overlap screen reports **zero** matches; the full five source histories have **not** been proven isolated from R45 by that screen. Four pairs of prospective cases share historical context; assess cluster/event dependence.
5. The Owner had explicitly accepted **AI-only R50 intake content review** according to the 2026-10-16 coordinator report; record that as an Owner review-policy exception, *not* an independent human signoff. It does **not** waive technical source, cross-world semantic, consent/agency, or future R56 **three independent blind model-reviewer** evaluation gates.

## Current safe gate ledger

| Gate | Evidence | Status |
|---|---|---|
| Original source integrity + time-bounded reference | 50/50 cases; 392/392 references; 50/50 card intervals | **PASS, limited to the checked source facts** |
| Count-only preseal set | 46 of 50; 5 worlds, 9/10/9/8/10 | **PASS as a candidate inventory** |
| AI-only candidate content triage | 46 retained, 4 excluded by Owner | **PASS as AI-only preliminary content decisions** |
| R45 actual Train49/Val15 source SHA | 2026-10-16 private reported check | **REPORTED PASS, not rerun here** |
| R45 vs 46 visible prompt text, 40/64-codepoint screen | No matches in that limited scope | **PARTIAL PASS only** |
| R45 vs **all 5 complete** source histories / 120-character all-offset screen | Prior code available; no verified output receipt here | **HOLD** |
| Earlier evaluation exposure, aliases, shared setting, paraphrases; target-time rule applicability | No conclusive independent cross-world semantic evidence | **HOLD** |
| 12 sequential User messages, canonical chat-role merge strategy | One unapproved draft exists | **HOLD** |
| True pinned Qwen tokenizer, context length/truncation | No actual tokenization run | **HOLD** |
| Exact same four-model input deployment contract + evaluation preregistration | Draft only; not signed | **HOLD** |
| Final private sealed input + grader/randomization custody | Not performed | **NOT SEALED** |
| Official new independent test admitted | None | **0** |

**Do not call the retained 46 `officially admitted` or the 50 original `sealed`.** The earlier R50 long-term W17 semantic/HOLD evidence is separate from an AI-only visible-content vote.

## Highest-value CPU-only Owner action, WITHOUT opening R50 case text to model developers

The repo **already contains** `scripts/v03_r50_private_r45_isolation.py` and its tests at pinned code commit `92828ac0e47c8f7f7307851b8e171f564fd065ed`. Git blob SHA-1 for this script: `0736ca7bb83787b2643819be27563255face7cc9`. Do not create a second overlapping checker.

On the Owner Mac, with the original R45 Train49 and Validation15 **JSONL** unzipped in a secure directory, have an authorized **separate audit operator**, not the model tuning operator, perform:

```bash
set -euo pipefail
cd "$HOME/workspace/storyforge"
SRC=a197923e1e15344e8c98bd96e593e84781b68c83
AUDIT=92828ac0e47c8f7f7307851b8e171f564fd065ed
CHECKOUT="$HOME/.local/share/storyforge/r50/r45-isolation-checkout"
OUT="$HOME/.local/share/storyforge/r50/r45-full-source-counts-v1.json"

# Pin the audit implementation and ensure frozen five-story source blobs did not change.
git cat-file -e "$SRC^{commit}"
git cat-file -e "$AUDIT^{commit}"
git diff --quiet "$SRC" "$AUDIT" -- evaluations/v0.2/source-archives/16-20
test ! -e "$CHECKOUT"
mkdir -p "$(dirname "$CHECKOUT")"
git worktree add --detach "$CHECKOUT" "$AUDIT"
mkdir -p "$(dirname "$OUT")"
chmod 700 "$(dirname "$OUT")"

python3 "$CHECKOUT/scripts/v03_r50_private_r45_isolation.py" \
  --repo "$CHECKOUT" \
  --train "/ABSOLUTE/PRIVATE/PATH/R45_TRAIN49_ORIGINAL.jsonl" \
  --validation "/ABSOLUTE/PRIVATE/PATH/R45_VALIDATION15_ORIGINAL.jsonl" \
  --output "$OUT"

# The output is aggregate-only; do not send the raw sources or private candidates.
```

**Important:** the two `--train/--validation` paths above are placeholders, not claimed actual filenames. Replace them with the already-held exact R45 original files matching the script's hardcoded SHA256 pins. Any missing file, mismatched source tree, unexpected match or failed test means **HOLD**. This scan does not by itself establish independence: aliases, paraphrases and shared-world semantics still need a separate evidence-backed adjudication.

After a valid count-only result, separately complete a **read-only real Qwen tokenizer audit** against the *frozen and approved* role construction, including all 12 double-User cases; do not silently merge User messages. The proposed 16,384 context / 1,536 reply budget is **not** approved simply because a draft exists. The next stage is the final input/score/model preregistration, *then* a one-time final seal and independently authorized inference.

## Do not cross protected boundaries

- No R50 user prompts, source-to-case mappings, private case hashes, reviewer answers, answer keys or raw novel text in normal Git, CI logs or model-developer threads.
- No access to the private sealed R50 input by this R56 coordination pass.
- No modification of original R45/R46/R50 data, no R50 model output, no paid GPU/HF Job, no model promotion.
- `R54_NOT_PROMOTED`; `R56_OFFICIAL_TEST_ADMITTED_0`; new world source discovery is closed because the Owner has no further originals.

**Status:** `R50_46_PRESEAL_SOURCE_EVIDENCE_RECONCILED__R45_FULL_HISTORY_HOLD__QWEN_ROLE_CONTRACT_HOLD__NO_FINAL_SEAL`.
