# W17 three-pair exact-source overlap targeted preflight

The owner-supplied full-LFS inventory returned exactly three linked
textual-duplicate flags: old 02↔new 17, 04↔17 and 10↔17.
Each contained one exact long message and five sampled 120-character
windows; story UUIDs were not equal. **This does not prove a shared world,
and is not enough to label the text benign boilerplate.**

The new standard-library-only runner
\`scripts/v03_r50_w17_source_overlap.py\` uses the same immutable old LFS
sources and frozen R50 source receipt to determine whether one literal
explains all three flags. It only outputs aggregate counts and source rank
numbers; never the messages, per-case IDs, source UUIDs or text hashes.

Run from an authenticated local Git checkout after fetching the audit branch:

\`\`\`bash
cd ~/workspace/storyforge
python3 -m unittest discover -s tests -p 'test_v03_r50_w17_source_overlap.py' -v

# Only full source overlapping literals, no HF access:
python3 scripts/v03_r50_w17_source_overlap.py --repo . \\
  --old14 evaluations/v0.2/training-readiness/20261013/private/original_chat_jsonl_14_20261013.zip \\
  --old06-15 evaluations/v0.2/source-archives/06-15/StoryForge_v02_06-15_Full_Evidence_20261013.zip

# Stronger: two authenticated PRIVATE Bucket reads only, NO HF Job:
python3 scripts/v03_r50_w17_source_overlap.py --repo . \\
  --old14 evaluations/v0.2/training-readiness/20261013/private/original_chat_jsonl_14_20261013.zip \\
  --old06-15 evaluations/v0.2/source-archives/06-15/StoryForge_v02_06-15_Full_Evidence_20261013.zip \\
  --stage-key r50-token-20261016T101504Z-77dc6606
\`\`\`

The stronger mode checks the 46-case file SHA and private generic System SHA
before measuring overlap of shared source text with the actual W17 held-out
history, world card, long-term rules, new user prompt and shared System.
Private input lives only in an ephemeral temp directory, automatically removed.

**Zero lexical overlap in private cases cannot rule out a semantic shared
character/event/world; any positive held-out text overlap still requires
AI review.** The full semantic graph gate remains HOLD. Nothing executes a
model or changes raw input. Do not call this a final seal.
