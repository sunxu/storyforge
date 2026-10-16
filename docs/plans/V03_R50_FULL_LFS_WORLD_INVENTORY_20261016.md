# R50 — Full original LFS world inventory (no GPU)

**Status: CODE ONLY / NOT YET EXECUTED ON REAL LFS PAYLOADS / SEMANTIC HOLD.**

The R45 frozen Train49/Val15 source story ranks are **02, 04, 06, 08, 09, 10, 12, 14, 15**. R45's scoped graph also records an **04↔07 linked component** outside the Train/Val set. The inventory intentionally covers all ten original worlds (nine + 07) against all five R50 sources (16–20): **50 pairs**, not just 45.

The private repository has the required original archives as Git LFS pointers:

| Original | Git location | Expected full payload SHA256 | Bytes |
|---|---|---|---:|
| Old 01–14 | `evaluations/v0.2/training-readiness/20261013/private/original_chat_jsonl_14_20261013.zip` | `050af7034f9b2f3ef0401542364d23ef6ce126dd1699a49b1124d69245c98fdb` | 57,602,487 |
| Old 06–15 | `evaluations/v0.2/source-archives/06-15/StoryForge_v02_06-15_Full_Evidence_20261013.zip` | `b874cd07547092e9c3c967f69fab6b75262ff4f44ba2d368fd575f84e8886afb` | 65,332,700 |

These sources were verified against Git LFS POINTER text in the current audit. The full payloads have **not** been retrieved independently in this chat. A former owner report says the 06–15 blob passed a fresh-clone SHA+ZIP CRC check; both payloads require local verification again.

## Git-native command

On a Mac checkout of `sunxu/storyforge`, with `git lfs` installed:

```bash
cd ~/workspace/storyforge
git fetch origin audit/r49-r50-source-intake-20261015
git switch audit/r49-r50-source-intake-20261015
git pull --ff-only origin audit/r49-r50-source-intake-20261015

# Only checks original archives; pulls about 123 MB from Git LFS;
# does not create any paid HF/GPU Job or send prompts to ChatGPT.
bash scripts/v03_r50_run_full_lfs_world_gate.sh scan

# After reviewing the aggregate report, optionally commit only sanitized
# counts and rank-pair flags to the R50 audit branch:
bash scripts/v03_r50_run_full_lfs_world_gate.sh --push
```

The program verifies immutable archive SHA256+ZIP CRC, all 14 direct historical original story records, one unique old-15 nested source, the tracked five R50 source transcripts/card identities, and an exact-ID / sampled 120-codepoint cross-world lexical screen. It emits only source rank numbers, counts, and flags, without any original names or text. The output remains outside Git unless `--push` is explicitly chosen. Neither outcome can certify hidden aliases, transformed characters, semantic paraphrases, or point-in-time card facts: **semantic HOLD remains until AI adjudication based on full original text**.

Potential causes of fail-closed HOLD include unavailable LFS binary, nested 15 record ambiguity, and mismatch of frozen source structure. The script does not rewrite originals, delete anything, generate text, run inference or create a final seal. If it HOLDs, share only its marker/error code, not raw story excerpts.
