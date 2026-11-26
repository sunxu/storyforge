# R50 W17 — locate the invalid evidence citation without exposing source text

Owner-local validator currently returns:

`R50_W17_PRIVATE_AI_REVIEW_VALIDATION_HOLD:
ValueError UNTRUSTED_OR_OUT_OF_SCOPE_EVIDENCE_PATH__OLD_RANK_2__POINTER_INDEX_8`

This locates **the ninth evidence citation of old 02↔17** (zero-based
index 8). The cited text/path is not available to the GitHub integration;
therefore it would be incorrect to auto-remove the citation or widen the
allowlist based on an unknown value.

Run after updating the audit branch:

```bash
cd ~/workspace/storyforge
git fetch origin audit/r49-r50-source-intake-20261015
git switch audit/r49-r50-source-intake-20261015
git pull --ff-only

REVIEW_DIR="$HOME/.local/share/storyforge/r50/private-ai-review"
python3 scripts/v03_r50_diagnose_w17_evidence_paths.py \
  --repo . \
  --kit "$REVIEW_DIR/W17_PRIVATE_AI_SEMANTIC_KIT_20261016.json" \
  --decisions "$REVIEW_DIR/W17_PRIVATE_AI_SEMANTIC_DECISIONS_20261016.json"
```

This performs **no AI model call**, no file mutations, and does not output
matched texts, source UUIDs, raw citations, arbitrary field names, or
free-form reviewer reasoning. It checks all three pairs in a single
pass and returns only **failing pointer indices** and safe classifications:
recognized root category, reference to old 02/04/07/10 (if any),
grammar support, whether the cited value actually exists in the immutable
SHA-pinned kit, and whether the current scoped allowlist covers it.

Interpretation:

- `VALID_KIT_FIELD_REQUIRES_HUMAN_SCOPE_REVIEW`:
  the path exists in Kit but is not within the scoped evidence allowlist.
  It may be legitimate corroborating context, but must **not** count as
  proof of identity of this old world without an anchored source reference.
- `INVALID_CITATION__REVIEWER_MUST_CORRECT`:
  the path cannot resolve in the frozen Kit; ask the original AI reviewer
  to correct its reference based on actually reading the source.
- `UNSUPPORTED_SYNTAX__REVIEWER_MUST_RECHECK`:
  the citation has a format the structural parser does not understand.
- `STRUCTURALLY_ACCEPTED` never proves the underlying inference valid.

Original `W17_PRIVATE_AI_SEMANTIC_DECISIONS_20261016.json` remains
unchanged. Do not delete pointer 8, forge an answer or silently approve
world separation. Semantic graph HOLD and NO_FINAL_SEAL remain.
