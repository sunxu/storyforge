# W17 seven-gap AI round 2: original full-message dossiers

**As of 2026-10-19:** first independent seven-gap AI workpaper has been
created and schema/source-pointer verified locally, SHA256
`6507ac6caec72aa031e9c70004a3d96781e7de8c0373976036c716aa9c884d9a`.

All 7 gaps remain `INSUFFICIENT_CONTEXT`; each cited 10 scoped
references, with 0 audited complete messages, `NOT_CHECKED` historical
card timing and 2 remaining requests per gap (14 reported requests total;
these may overlap). This is not a conclusion of semantic independence.
The 70 hit count also reflects saturated top-two lexical retrieval.

## Required evidence escalation, not another top-two search

Build a read-only full-message source dossier to address the missing
scope. It will use the **exact validated private workpaper**, previously
pinned seven gap packets and immutable original-source ZIP, then:
- cross-check each previously cited message's SHA256, codepoint length,
  source rank, index, role and exact prior excerpt against the source;
- include the **complete original message** and up to two **complete**
  messages before and after it, without truncation;
- deduplicate repeated messages within each gap while retaining citation
  rank and source message index;
- output seven independent private dossiers and a digest manifest under a
  new 0700 directory, with 0600 files and no Git/source writes;
- explicitly leave the character-card cutoff and world-graph semantics
  `HOLD` (the selected source transcript does not by itself certify
  which author/public character card applied to every prior turn).

Owner-local run after pulling branch:

```bash
cd ~/workspace/storyforge
git fetch origin audit/r49-r50-source-intake-20261015
git switch audit/r49-r50-source-intake-20261015
git pull --ff-only

ROOT="$HOME/.local/share/storyforge/r50/private-ai-review"
python3 scripts/v03_r50_build_w17_full_source_dossiers.py \
  --repo . \
  --packets-dir "$ROOT/W17_SEVEN_GAP_CONTEXT_PACKETS_20261019" \
  --workpaper "$ROOT/W17_SEVEN_GAP_AI_WORKPAPER_PRIVATE_20261019.json" \
  --old14 evaluations/v0.2/training-readiness/20261013/private/original_chat_jsonl_14_20261013.zip \
  --output-dir "$ROOT/W17_SEVEN_GAP_FULL_SOURCE_DOSSIERS_20261019"
```

This does **not** call an AI provider or GPU. These dossiers contain raw
private stories and reviewer notes, so **never put them in ordinary Git**
or include their content in terminal logs. The data is only for a new
authorized reviewer (cloud disclosure requires separate owner opt-in).

The output does not automatically resolve the seven gaps: complete
story arcs not represented by ±2 messages and point-in-time card
version/active rule evidence may still be missing. A future independent
semantic reviewer must adjudicate **identities and unique events**, and
record as `INSUFFICIENT_CONTEXT` when the source is still insufficient.

No modifications to original 46 candidate cases, R45 train/val,
existing private AI decision, previous workpaper or review Kit.
`SEMANTIC_HOLD` and `NO_FINAL_SEAL` persist.
