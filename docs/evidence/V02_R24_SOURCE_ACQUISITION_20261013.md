# StoryForge v0.2 — R24 exact source acquisition (2026-10-13)

**Training admission remains `PENDING_NOT_APPROVED`.** This is not an authorization to train, alter frozen Gold, or assign Train/Validation/Test.

## Verified checkpoint

- Inherited R23 source evidence ZIP SHA256: `9fdc43839ae2ab03a7648eaaac4bfe35d35d7a2a1962d1c972281517f064de76`.
- R23 exact source manifest: **13 original chat export basenames and file SHA256s**, SHA256 of CSV `e0a358c7ef665997605fa1edccfec0f9a2a0a7a09f6c6ba5cd86e0cff7e1812f`.
- R23 40 target-message UUID / Gold-text-hash join requests, SHA256 of CSV `acca3b135763b594b92d509f269bc409586f5508c3b1a69328ec03afbcb77cb8`.
- Local conversation artifacts (including supplementary `evidence.zip` children) contain card versions, relationship checkpoints and audit witnesses, **not** the original 13 byte-identical `by-story/*.json` source chat exports.
- Real-source check **0/13 verified exact export files; 0/40 source-based target timestamps**. No snapshot `created_at` was substituted for the target message creation time.
- Original R23 verifier was re-executed on an empty source folder: **exit 2 / BLOCKED**. The new R24 source-acquisition verifier likewise yielded **exit 2 / BLOCKED** with 13 missing sources and 40 blocked joins.
- New standalone R24 Python tool supports explicit `--source-dir` and `--source-zip`, exact hash and target joins, timezone-aware `created_at`, and no raw text output. Tested on **seven synthetic cases**: valid sources, ZIP, missing, altered content, duplicate identical sources, naive timestamps and tampered manifest. Seven of seven unit tests pass. **No synthetic result is asserted as original source evidence.**
- Independent R24 ZIP extraction and verifier PASS; simulated tampering correctly rejected.
- Private R24 artifact SHA256: `7eb5d140a1c172d5c5dc82dd0e1241c9ba2d12591e7f124030f00206b9c30321` (211,764 bytes). R24 artifact is delivered in ChatGPT, **not stored in this repository**.

## Owner-side next command

Download the R24 ZIP from the original chat and unzip locally. Find the 13 byte-identical original exports whose basenames/expected hashes are in the private CSV. The supplementary `D:\\git-source\\RolePlay\\artifacts\\chat-data\\...\\by-story` is a historical Windows path reference, not an accessible path automatically available on macOS.

```bash
python3 r24_locate_and_join_sources.py --source-dir "/absolute/path/to/chat-data" --output-dir "/private/path/to/r24-results"
# Or replace --source-dir with --source-zip "/absolute/path/to/original-exports.zip"
```

The tool writes only source-file status, candidate IDs, verified creation timestamps (when present), and gate counts, not chat replies or card bodies. **Do not commit original source JSON/ZIP or the private timestamp CSV to GitHub.** If source bytes are unavailable, exit 2 and BLOCKED are the *correct results*.

Even after 13/13 and 40/40 succeed, that proves only original message identity and timestamps. Request-effective story-card version joins, age/consent approvals, linked-world/held-out isolation, final dataset re-tokenization and split gates remain independently unapproved. R18 40/40 historical diagnostic is unchanged.