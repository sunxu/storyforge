# R50 W17: private seven-gap original-source locator

**State: code prepared; no local seven-gap inventory executed; semantic HOLD.**

The user's original W17 AI verdict passed validation and was pushed at
commit `498135b8a0fc95c7405ccd74459d97c198297c97`; the private
decision-file SHA256 is
`61e4aa21370c2f9f8ef84d648fb600f51e2fa151e30e25999bb328f23da581bf`.

The three W17 pair decisions are **all INSUFFICIENT_EVIDENCE**. Their
evidence reference counts are 9/9/8. The independent AI listed seven
specific missing evidence requirements, but these are **not stored in Git**.

Instead of guessing the seven requirements from categories, the new script
`scripts/v03_r50_index_w17_seven_gaps.py` reads the exact frozen private
decision file, checks the SHA256 against the archived Git receipt, verifies
the original 01–14 LFS ZIP and W17 Git source/card bytes, then builds a
**private lexical-only candidate index** for all seven requirements over
old 02/04/07/10 and new W17 source messages. A high score means
character n-gram overlap, **not** identity or plot connection. Every
candidate excerpt has an original message index and a limited excerpt;
no source story text prints to stdout or enters Git.

## Run read-only candidate discovery on the authorized Mac

```bash
cd ~/workspace/storyforge
git fetch origin audit/r49-r50-source-intake-20261015
git switch audit/r49-r50-source-intake-20261015
git pull --ff-only

python3 -m unittest discover -s tests \
  -p 'test_v03_r50_index_w17_seven_gaps.py' -v

ROOT="$HOME/.local/share/storyforge/r50/private-ai-review"
python3 scripts/v03_r50_index_w17_seven_gaps.py \
  --repo . \
  --kit "$ROOT/W17_PRIVATE_AI_SEMANTIC_KIT_20261016.json" \
  --decisions "$ROOT/W17_PRIVATE_AI_SEMANTIC_DECISIONS_20261016.json" \
  --old14 evaluations/v0.2/training-readiness/20261013/private/original_chat_jsonl_14_20261013.zip \
  --output "$ROOT/W17_SEVEN_GAP_PRIVATE_SOURCE_INDEX_20261019.json"
```

The script never calls external models, creates HF jobs, writes to Git,
or overwrites a preexisting private index. It requires the output parent
directory to be private (no group/other access), and writes 0600 output.
It prints only a success marker and private index SHA256, not missing
requirements, excerpts, names or reviewer reasoning.

The resulting private index contains the seven **actual reviewer-stated
gaps** and at most two candidate excerpts per each of five sources per gap.
It is a preliminary source locator; it does **not** establish the missing
evidence is actually present. AI reviewer should read the full relevant
original exchanges and valid historical card versions, independently
classify evidence supported/not found/unavailable, and produce a **new**
private decision version without modifying the original one. If not enough
evidence exists, retain INSUFFICIENT_EVIDENCE.

The known 04↔07 connected component and all final gates remain on HOLD.
No new model response generation, model promotion or final Held-out seal.
