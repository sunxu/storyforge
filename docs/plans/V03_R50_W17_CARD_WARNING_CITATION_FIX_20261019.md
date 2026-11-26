# R50 W17 — W17_CARD_HINTS citation scope: pinpoint correction

The owner-local **read-only** diagnostic of the frozen W17 private
AI decision file reported **26 citations checked, three flagged**:

| Reviewed pair | 0-based pointer index | Root | Exists in pinned kit |
|---|---:|---|---|
| 02↔17 | 8 | W17_CARD_HINTS | yes, nonempty |
| 04↔17 | 8 | W17_CARD_HINTS | yes, nonempty |
| 10↔17 | 7 | W17_CARD_HINTS | yes, nonempty |

All three have VALID syntax and OUTSIDE_SCOPED_ALLOWLIST. Comparing the
frozen private Kit **builder schema** with the existing validator allowlist
shows just one valid field under `w17_export_card_review_hints` not already
covered by the allowlist: **`WARNING`**.

The builder explicitly writes:

```text
"WARNING": "Export-time card is not automatically valid at test cutoff"
```

**That field is an epistemic caution, not W17 content/identity evidence.**
It is appropriate for a reviewer to cite it as a *limitation*, but
must not count toward the W17-side positive-evidence threshold for
`WORLD_LINK` or `CLEAR_WITH_EVIDENCE`. This is therefore not an
exception allowing arbitrary other role-card fields.

## Implementation boundary

The validator permits only the exact two-component path
`w17_export_card_review_hints.WARNING`, classifies it as
`context` rather than `new`, and still confirms that the pointer
resolves within the byte-exact SHA256-pinned Kit. Every unrelated card
field or invented pointer remains rejected. The existing requirement
for substantive anchors from both the relevant old source and W17 is
unchanged.

This diagnosis is logically derived from the published builder structure
and owner-provided **non-textual** diagnostic classification. The assistant
has **not** directly read the private decision file or independently
verified its three exact raw citation strings. If rerunning still
fails, use the private diagnostic again; do not edit/rewrite the
independent reviewer decision to satisfy the validator.

## Read-only recheck

```bash
cd ~/workspace/storyforge
git fetch origin audit/r49-r50-source-intake-20261015
git switch audit/r49-r50-source-intake-20261015
git pull --ff-only

REVIEW_DIR="$HOME/.local/share/storyforge/r50/private-ai-review"
python3 scripts/v03_r50_verify_w17_ai_decisions.py --repo . \
  --kit "$REVIEW_DIR/W17_PRIVATE_AI_SEMANTIC_KIT_20261016.json" \
  --decisions "$REVIEW_DIR/W17_PRIVATE_AI_SEMANTIC_DECISIONS_20261016.json"
```

**Scope:** path/schema verification only, not independent substantive
review of the 02↔17 / 04↔17 / 10↔17 conclusions. Full semantic graph
**HOLD**, Held-out final seal **NOT_PERFORMED**, no HF Job/GPU/inference,
no modifications to 46 cases or reviewer decision.
