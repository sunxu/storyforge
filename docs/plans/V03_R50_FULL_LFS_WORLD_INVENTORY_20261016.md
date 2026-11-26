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

## 2026-10-16: old14 duplicate-rank parser correction

An actual owner-side scan failed with `OLD14_RANK_COLLISION`. The previous
parser treated **every** root ZIP entry beginning with `NN-` as a unique
story, without accounting for alternate exported representations.

The corrected parser groups root-level `NN-*.json` and `NN-*.jsonl`
chat entries by rank. It permits multiple representations only when the
source story ID and complete ordered sequence of message role and exact
content are equal. It rejects any altered/missing ID, changed transcript,
malformed message, missing rank or invalid ZIP payload. Unrelated TXT
sidecars are ignored. No prior data are silently selected without
cross-validation. The exact list of member names in the actual old14
archive has not been disclosed or independently inspected here; this
change addresses the ambiguous-rank failure mode conservatively.

Three new synthetic checks cover JSON/JSONL pair equivalence,
contradictory transcripts and contradictory source identity. No GPU,
HF Job, test generation or final Held-out seal is performed.

## Follow-up: OLD14_UNEXPECTED_SOURCE_RANK (root-cause correction)

The old14 ZIP has additional numbered root-level JSON/JSONL candidates
beyond the presumed range 01–14. The archive name describes the number
of source exports; it is **not** an authoritative guarantee of contiguous
numeric ranks. The previous parser rejected an extra rank before checking
the actual nine-world R45 source coverage.

The revised check parses all two-digit numbered source records (01–99),
demands the specific R45 historical ranks 02/04/06/07/08/09/10/12/14
(15 is independently verified from the 06–15 LFS archive), reconciles
all JSON/JSONL variants, and records extra source ranks in the
*aggregate* report. Unexpected extra ranks cannot override frozen required
stories. Their source IDs are compared against R50 identities and any
conflict creates a flagged result; an optional rank-15 representation in
the first archive must match the second archive exactly.

This was added in response to the owner's real-world
`R50_LFS_SOURCE_INVENTORY_HOLD: ValueError OLD14_UNEXPECTED_SOURCE_RANK`.
The complete LFS ZIP member listing is still not available through the
ChatGPT GitHub connector; no claim is made that the real run has passed.
The source archives and existing dataset hashes remain unchanged.

## 2026-10-16: BAD_NEW_WORLD_FOLDER on macOS

The owner reported `R50_LFS_SOURCE_INVENTORY_HOLD: ValueError
BAD_NEW_WORLD_FOLDER` after the old-source archive stage. The prior scanner
incorrectly required **all** root entries under `16-20/` to be directories.
The five immutable R50 world folder names, numeric ranks and source identities
are already pinned in `V03_R50_SOURCE_16_20_RECEIPT_20261015.json`.

The patched scanner reads only those **five expected directories**, requires
all five to exist exactly, and allows only explicitly identified macOS
non-symlink regular-file metadata beside them: `.DS_Store`, `.localized`,
and `._*`. It refuses unknown files/directories and **all root symlinks**
(including a symlink pretending to be an ignorable metadata sidecar).
Within each frozen world it still checks the JSONL, story-card, rank, story ID
and (where supplied in the receipt) session ID.

Six pure synthetic test cases were added to prevent silent skips, missing
worlds, unrecognized root entries and metadata symlink bypass. This patch is
not an assertion that the actual Mac has a `.DS_Store` (the GitHub connector
cannot inspect the owner's local untracked files). No archive bytes or frozen
inputs are rewritten; semantic isolation remains HOLD.
