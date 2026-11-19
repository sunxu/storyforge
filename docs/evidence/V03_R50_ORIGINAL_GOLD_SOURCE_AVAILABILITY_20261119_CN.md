# StoryForge R50 — Original Gold source availability SAFE receipt

**Date:** 2026-11-19  
**Repository:** `sunxu/storyforge`  
**Branch:** `docs/r50-agent-handoff-20261119` (Draft PR #33; not merged)  
**Scope:** read-only reconciliation of already-existing source evidence. No private conversation text, case IDs, source-message IDs, per-case mappings, answers, or raw review materials are included.

## 1. Evidence tiers

- **Owner-provided local verification output:** archive sizes, SHA256, ZIP CRC and byte-identical comparison pasted by the Owner in the current conversation. The agent did not independently access the Owner Mac filesystem or re-read the ZIP bytes.
- **Repository artifact independently inspected:** `docs/evidence/V03_R50_REAL_SOURCE_REPLAY_20261016.json` on `audit/r49-r50-source-intake-20261015`, source commit `a197923e1e15344e8c98bd96e593e84781b68c83`.
- **Bounded Library inventory result:** 106 R50 Library artifacts were previously searched; no dedicated R50 Original Gold reply package was found in that searched directory. This is not an exhaustive inventory of every Owner-held storage location.

## 2. Owner-reported archive integrity

| Archive | Owner-reported bytes | SHA256 | ZIP CRC | Additional result |
|---|---:|---|---|---|
| `original_chat_jsonl_14_20261013.zip` in Downloads | 57,602,487 | `050af7034f9b2f3ef0401542364d23ef6ce126dd1699a49b1124d69245c98fdb` | PASS | — |
| Same archive in repository private path | 57,602,487 | Same expected SHA256 | PASS | `cmp` reported `IDENTICAL` |
| `StoryForge_v02_06-15_Full_Evidence_20261013.zip` | 65,332,700 | `b874cd07547092e9c3c967f69fab6b75262ff4f44ba2d368fd575f84e8886afb` | PASS | — |

These results confirm that the two local copies of the 14-chat archive are byte-identical and that both archives match the repository's historical expected size/hash values. They do not add new source-message or Original Gold evidence. Do not repeat CRC/hash checks on these unchanged bytes.

## 3. Existing source replay rules out exact prompt reuse in the five pinned R50 source transcripts

The 2026-10-16 R50 source replay receipt records:

- 50 new R50 user inputs;
- 5 pinned source worlds (ranks 16–20);
- 392/392 historical message references exact-matched;
- 50/50 contiguous source-history and cutoff checks;
- `source_input_normalized_verbatim_reuses = 0`.

The replay method explicitly compared the original 50 new User inputs against source User messages for normalized verbatim reuse. Since byte-identical input would necessarily be a normalized verbatim reuse, the receipt rules out an exact current-User-input match in those five pinned source transcripts.

The protected 46-case set is a subset of the frozen 50. Therefore:

```text
PINNED_FIVE_WORLD_EXACT_USER_INPUT_MATCHES = 0 / 50
PINNED_FIVE_WORLD_ORIGINAL_GOLD_ELIGIBLE = 0 / 46
```

This is a conclusion about the five pinned source transcripts only. The 14-chat and 06–15 archives have now been integrity-verified by the Owner, but no new exact full-history matching scan was performed against them. A text-only match in a different story would not qualify as Original Gold unless the complete preceding history, role/order/content, System, Card, Rules, cutoff and original Assistant provenance also matched.

## 4. Original Gold disposition

The R50 comparison contract requires the same current User input, exact preceding history, same System/Card/Rules as of cutoff, authenticated original Assistant reply and source-byte hash. Similar questions, same-story answers, adjacent-turn answers, later edits, Gold195, or newly generated text cannot substitute.

Current bounded conclusion:

- No Original Gold is eligible from the five pinned R50 source transcripts for the protected 46.
- No dedicated R50 Original Gold reply package was found in the previously searched 106-item R50 Library inventory.
- The Owner's verified 14-chat and 06–15 archive binaries are available for future targeted read-only source lookup, but their existence alone does not establish a qualifying same-history reply.
- Overall Owner-wide Original Gold coverage remains `NOT_ESTABLISHED` until any additional source store is searched or the Owner confirms there are no other candidate source stores.

Do not label the overall result `0/46` across all possible Owner-held sources. The supported statement is `0/46` eligible in the five pinned R50 source transcripts, with wider source-store coverage not yet exhausted.

## 5. Next minimal action

If the Owner authorizes it, perform a single read-only exact-match lookup against the verified 14-chat and 06–15 archives, comparing the frozen R50 user input **and complete preceding history** and emitting only aggregate counts. Do not repeat archive integrity checks, the 2026-10-16 five-world replay, W17 lexical scans, or prior W17 AI reviews. Do not output source text, identifiers, mappings or answers.

No HF Job, tokenizer Job, model inference, GPU, training, answer-key access, unblinding, final seal or promotion was performed or authorized by this receipt.

## 6. Gate state

```text
ORIGINAL_GOLD_R50_COVERAGE = NOT_ESTABLISHED
PINNED_FIVE_WORLD_ORIGINAL_GOLD_ELIGIBLE = 0 / 46
WORLD_SEMANTIC_ISOLATION = HOLD
TIMEPOINT_CARD_RULE_PROVENANCE = PENDING
HIDDEN_ALIAS_WORLD_COMPONENT_CLOSURE = HOLD
CPU46_TOKEN_LENGTHS = VERIFIED_DRAFT_ONLY
ROLE12_STRUCTURE = PASS_AS_REPORTED
ROLE12_POLICY = APPROVED
FOUR_ARM_RUNTIME_ROLE_PARITY = NOT_VERIFIED
OFFICIAL_HELDOUT_ADMITTED = 0
FINAL_SEAL = NOT_PERFORMED
GPU_USED = false
MODEL_INFERENCE_RUN = false
TRAINING_RUN = false
```


## 7. Supplementary archive scope reconciliation — 2026-11-19

The Owner subsequently ran read-only scans against the two integrity-verified ZIPs.

- The 14-chat ZIP contains 28 `.jsonl` entries: 14 actual conversation exports and 14 AppleDouble macOS metadata entries (206 bytes; magic `00051607`). All 14 actual conversations parsed, totaling 62,583 messages. The 14 metadata entries are not JSONL and must be skipped by magic-byte classification; the archive itself is not damaged.
- The 06–15 archive contains 32 nested ZIPs; the recursive scan parsed 100 JSON/JSONL entries and 1,010 conversations (71,884 messages), with no parser errors.
- The Owner-run exact-history scan reported zero content-sequence occurrences in either archive. The subsequent Message-ID-first diagnostic emitted no positive match counters for either archive; its output was empty after each archive's match heading. No source text or identifiers were emitted.

These archives are supplementary historical collections (14-chat and source ranks 06–15), not the five pinned R50 source transcripts (worlds 16–20) used by the authoritative 2026-10-16 replay. Their lack of the R50 provenance Message IDs is therefore expected and does not invalidate the authoritative 392/392 replay. Do not rerun the ID-first scan or continue treating these archives as candidate same-history Gold sources without a new, independent provenance lead.

The authoritative R50 replay already compared all 50 new User inputs against User messages in the five pinned source transcripts and recorded zero normalized verbatim reuses. Since the protected 46 are a subset, there is no same-current-User Original Gold in those five source transcripts. The supplementary archives did not surface a qualifying same-history source. Current bounded disposition is therefore: 

```text
PINNED_FIVE_WORLD_ORIGINAL_GOLD_ELIGIBLE = 0 / 46
SUPPLEMENTARY_14_CHAT_EXACT_HISTORY_MATCHES = 0 OBSERVED
SUPPLEMENTARY_06_15_EXACT_HISTORY_MATCHES = 0 OBSERVED
ORIGINAL_GOLD_R50_COVERAGE = NOT_ESTABLISHED_OUTSIDE_EXAMINED_SOURCES
```

The phrase `0 / 46` applies to the five authoritative pinned R50 source transcripts, not every conceivable Owner-held source. No new Original Gold candidate was found. The four-model comparison remains the valid default for cases without Gold; any historical continuation after the cutoff must be labelled as a different reference type and must not be scored as a response to the appended current User input.

No archive was modified. No original text, IDs, mappings or answers were committed. No tokenizer/HF job, inference, GPU, training, admission, final seal or promotion occurred.
