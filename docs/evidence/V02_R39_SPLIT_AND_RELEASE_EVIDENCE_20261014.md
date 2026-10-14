# StoryForge v0.2 — R39 final signoff & disjoint-split preflight (2026-10-14)

**Training admission remains `PENDING_NOT_APPROVED`; no HF CPU/GPU job or training optimizer was run.** User approved the experimental R27 generic no-card input design only. Frozen 195 quality Gold, 117 source-derived rows, and 82 conditional candidates remain unchanged.

## Inputs and verified evidence

- User-provided R38 ZIP `StoryForge_v02_R38_Subset_Inheritance_And_Split_20261014.zip` SHA256 `b4bbfcb5953d0d4337a25f57481ce55793731058966035be418bf8b046a61ddc`.
- Its nested R37 original 82-row JSONL SHA256 `f108c2b85ae096fd00e49e23e50d00b1cf0cf779682793ea6e3951e700b9e7c9`.
- [Independent R38 Github LFS verification](https://github.com/sunxu/storyforge/actions/runs/38428606867) already tied all 82 unchanged rows to the real HF Job `6ace19935ccb47ba0f787af5`: **155,946 original ms-swift tokens, 21,807 supervised tokens**. No additional CPU Token/Mask work was billed by R39.
- R39 local verifier replayed exact 82 target hashes, final-only loss flags, unchanged `NOT_APPROVED` admission metadata and raw byte-identical Train/Validation *proposals*.

## Split alternatives reconstructed, not authorized

| Provisional whole-story proposal | Train | Validation | Validation by story | SHA256 Train / Validation |
|---|---:|---:|---|---|
| R37 unchanged | 65 | 17 | 16, 1 | `7e696f99...` / `fb66cbcf...` |
| **A, preferred for balance subject to review** | **64** | **18** | **8, 8, 2** | `349b4d30...` / `84d6eea7...` |
| B, more worlds | 66 | 16 | 8, 5, 2, 1 | `b10e9084...` / `4df484e9...` |

R37 Validation is dominated by one story (16/17, 94.1%). A mitigates that problem; B includes one additional story but has fewer Validation samples. Every scenario preserves original row bytes; **no scenario is signed or world-component-certified**.

R39 systematically checked all **36 unordered pairs among the nine story UUIDs**, using normalized exact non-System dialogue substrings, and found:
- **4 story pairs** share one or more **12-character** segments (could be formulaic descriptions).
- **0 story pairs** share **16-character** or **24-character** segments.
- **Do not infer shared IP/character identity from short phrase matches or independence from longer phrase nonmatches.** Names like `绵绵` can be common words as well as nicknames. The required human-reviewed alias graph and original source provenance remain unsigned.

## New concrete artifacts

Private archive `StoryForge_v02_R39_Release_Evidence_And_Loader_20261014.zip` SHA256 `edee5d7ec0d2f795dd70ab760127afc3ec198ca53a9c93e964e67c859e4a4711` contains:
- An **82-row ID/hash-bound final signoff worksheet**, all `PENDING` and `NOT_APPROVED`.
- A **9-world rights and alias certificate worksheet**, no component assigned or signed.
- Original-line **A/B proposal-only JSONL**; no official `train.jsonl`.
- Short lexical pair metrics, hashes, R38 evidence parent, 2-world/20-prompt **fresh independent human-heldout intake criteria** (still no actual heldout), a no-GPU release gate, and an offline source/line replay validator.
- Local complete verification marker: `R39_82_SOURCE_AND_A_B_SPLIT_BYTE_REPLAY_PASS__4_SHORT_LEXICAL_PAIRS__ALL_RELEASE_GATES_BLOCKED`. An intentionally tampered signed-status row was rejected with exit 2. The release gate itself explicitly exits 2.

The ZIP **contains private narrative content** in its nested source and candidate files; it is not uploaded in ordinary Git. Only this summary, machine-readable status and code-only repeatable checks belong in the private repo.

## R40 should focus on missing real decisions, not more lexical audits

- Independent, signed content/age/consent/player autonomy review for each selected candidate; resolve hard evidence issues by holding sample, not rewriting Gold.
- Actual story/world/character/IP/permissions linkage and v0.1 independence declaration for each of 9 groups. The 25 original third-party-origin cases stay quarantined.
- **Two genuinely new independent user/contributor-provided worlds with >=20 never-used evaluation prompts, cryptographic custody, human attestations and sealed labels**. No available existing archive or assistant-generated smoke tests can substitute.
- Choose and sign A/B whole-component split; run real final compiled loader/batching/packing test on that exact dataset if necessary.
- **Explicit separate GPU authorization** after all gates; none currently exists.

**The R39 completion is engineering evidence and review documentation, not a formal dataset release.**