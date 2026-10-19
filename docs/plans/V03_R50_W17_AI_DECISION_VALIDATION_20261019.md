# StoryForge R50 — W17 independent AI review acceptance gate

Owner reported W17 private meaning-review kit successfully built, with
SHA256 `0c1dccd8de0926ab416a85ccb77f474e668138938171f0419eb43ce582a99cc3`.

**This establishes a content-addressed input to a future independent reviewer,
NOT a semantic verdict.** The file is located on the owner's Mac and the
assistant/GitHub connector cannot read its bytes directly.

The independent reviewer uses the already-frozen task:
`docs/plans/V03_R50_W17_INDEPENDENT_AI_REVIEW_TASK_20261016.md`.
Reviewer must write their own private
`W17_PRIVATE_AI_SEMANTIC_DECISIONS_20261016.json` in the same restricted
directory. They must actually read and evaluate the private kit, avoid
blindly adopting the task's expected hypotheses, and report limited/uncertain
evidence as `INSUFFICIENT_EVIDENCE`. Do not upload the private kit or decision
text to ordinary Git, CI logs or arbitrary public AI endpoints.

After a reviewer has generated that file, run locally:

```bash
cd ~/workspace/storyforge
git fetch origin audit/r49-r50-source-intake-20261015
git switch audit/r49-r50-source-intake-20261015
git pull --ff-only

REVIEW_DIR="$HOME/.local/share/storyforge/r50/private-ai-review"

python3 -m unittest discover -s tests \
  -p 'test_v03_r50_w17_ai_decision_validator.py' -v

# Non-mutating verification first:
python3 scripts/v03_r50_verify_w17_ai_decisions.py --repo . \
  --kit "$REVIEW_DIR/W17_PRIVATE_AI_SEMANTIC_KIT_20261016.json" \
  --decisions "$REVIEW_DIR/W17_PRIVATE_AI_SEMANTIC_DECISIONS_20261016.json"

# Optional ONLY if actual independent review was completed/checked:
python3 scripts/v03_r50_verify_w17_ai_decisions.py --repo . \
  --kit "$REVIEW_DIR/W17_PRIVATE_AI_SEMANTIC_KIT_20261016.json" \
  --decisions "$REVIEW_DIR/W17_PRIVATE_AI_SEMANTIC_DECISIONS_20261016.json" \
  --push
```

The verifier reads private 0600 files outside Git, compares the *entire*
kit to its pinned 64-character SHA256, rejects invalid status, missing 02/04/10
pair rulings, spurious evidence pointers, unanchored strong decisions, missing
04↔07 graph edge, and bad outcome enums. It writes **only categories and
counts** to Git with an explicit `--push`, never raw evidence,
verbatim story text, free-form rationale, reviewer transcript or names.

The validator does NOT judge AI reasoning quality or establish reviewer
independence. Even three `CLEAR_WITH_EVIDENCE` decisions do not automatically
remove the global R50 semantic graph HOLD. The five new worlds / ten old-world
graph and temporal provenance still need separate approval before any
Held-out seal.
