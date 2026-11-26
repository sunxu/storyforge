# R50 W17 — nested private evidence path validator fix

The owner reported `UNTRUSTED_OR_OUT_OF_SCOPE_EVIDENCE_PATH` after their
independent AI reviewer generated the private decisions file. The file reached
the verifier; this indicates a citation **format / allowed-scope** issue and
does not itself establish whether the AI's substantive judgement is correct.

The previous code only allowed a handful of section-level evidence paths,
whereas the private kit contains nested material such as:

```text
old_world_contexts.2.context_examples[0].neighbors[1].text_excerpt
w17_context.context_examples[0].neighbors[0].text_excerpt
w17_export_card_review_hints.character_briefs[0].name
```

The corrected validation routine accepts qualified nested paths in these
bounded sections, including JSONPath-like quoted-key syntax, **only when
the exact path resolves to a member of the immutable, SHA-pinned private
Kit**. It enforces numeric-index bounds, rejects private path traversal,
cross-old-world references, nonexistent fields, and duplicate normalized
citations. Strong `WORLD_LINK`/`CLEAR_WITH_EVIDENCE` decisions must still
cite meaningful material on **both** the specific old world and W17.

**Do not regenerate or rewrite the independent AI decision file merely to
make it pass.** First rerun the new synthetic-only tests and the read-only
validator against the unchanged private kit and private decision file:

```bash
cd ~/workspace/storyforge
git fetch origin audit/r49-r50-source-intake-20261015
git switch audit/r49-r50-source-intake-20261015
git pull --ff-only

python3 -m unittest discover -s tests \
  -p 'test_v03_r50_w17_ai_decision_validator.py' -v

REVIEW_DIR="$HOME/.local/share/storyforge/r50/private-ai-review"
python3 scripts/v03_r50_verify_w17_ai_decisions.py \
  --repo . \
  --kit "$REVIEW_DIR/W17_PRIVATE_AI_SEMANTIC_KIT_20261016.json" \
  --decisions "$REVIEW_DIR/W17_PRIVATE_AI_SEMANTIC_DECISIONS_20261016.json"
```

If the reviewer made up a field name, the validator will now stop with
`EVIDENCE_PATH_NOT_FOUND_IN_PINNED_KIT__OLD_RANK_N__POINTER_INDEX_I`
or `UNTRUSTED_OR_OUT_OF_SCOPE_EVIDENCE_PATH__OLD_RANK_N__POINTER_INDEX_I`.
These diagnostics never print the private pointer itself or any story text.
In that case, an **independent reviewer must correct their evidence citation
against the actual Kit** and preserve the original decision file as immutable
evidence; do not have a helper fabricate one or silently replace it.

**Boundary:** validation checks structural citation existence and scope, not
semantic correctness, causal support, reviewer independence, or complete
world-graph certification. All 46 cases remain frozen and the global
`SEMANTIC_HOLD` and `NO_FINAL_SEAL` remain in force.
