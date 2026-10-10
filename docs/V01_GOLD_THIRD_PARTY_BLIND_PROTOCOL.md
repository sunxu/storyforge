# StoryForge v0.1 — Independent Third-Party Gold Review Protocol

**Prepared:** 2026-10-10  
**Status:** `ANONYMIZED_PACKS_READY / EXTERNAL_GRADING_PENDING`  
**Historical evidence tag (immutable):** `v0.1-evidence-frozen` → `d1186a731a81219f86eb81b89ac1440dd116e9f4`

## Purpose

Compare the canonical 20 selected Gold continuations with the original Base and the v0.1 Adapter outputs. This is **retrospective v0.1 quality diagnosis**, not v0.2 training or a new held-out generalization test. A third-party review cannot be claimed until reviewers who have not seen the A/B source identities submit scored results.

The current assistant has previously encountered the model-answer mapping, so its own qualitative review is **not** counted as independent/third-party evidence. New reviewers must be genuinely blind to the mapping and prior outcomes.

## Predeclared assignment

- **six independent reviewer packs, 20 different original test prompts each; each Gold vs Base pair judged by 3 reviewers and each Gold vs Adapter by 3 reviewers; 120 total ratings, 40 unique pairs; per reviewer 10 of each comparator and balanced A/B 10/10; no source prompt repeated within reviewer.**
- Balanced incomplete-block design: assign each of 20 original samples a different size-3 subset of six reviewers (all `C(6,3)=20` combinations). That trio rates the Gold/Base pair and the complementary trio rates the Gold/Adapter pair.
- Each reviewer sees **only 20 different original sample prompts**, never two pairs from the same source prompt. Every reviewer receives ten Gold/Base and ten Gold/Adapter cases (those identities remain hidden), with ten reference responses in A and ten in B.
- Each case is presented under a fresh anonymized ID and independently shuffled. All six packages are isolated; organizers keep the hidden comparison/role mapping separately.
- To remove a direct identity cue, strip **only** the empty leading `<think>...</think>` wrapper from model outputs. No semantic narrative content changes. Record SHA256 of original and display text in organizer-only audit mapping.
- The prior blind materials were superseded because their filenames named `Gold_vs_BASE` / `Gold_vs_ADAPTER` and their model responses contained an empty thinking wrapper; **do not distribute the earlier packages as an independent third-party review**.

## Required scoring

Each reviewer independently scores 20 rows without access to GitHub evidence, an answer key, earlier assistant conversations, other reviewer sheets or any model identity. Each anonymous A and B gets a 1–5 integer score for continuity, character consistency, instruction adherence, prose, and interactive progress; each case must have A/B/TIE preference, a concrete cited reason, optional severe-issue detail and reviewer confidence (high/mid/low).

Use six genuinely independent judges, or explicitly label any sessions that share reviewers/models as non-independent. Fresh isolated assistant chats are a practical but weaker proxy for independent third-party humans; do not overstate that design.

## Integrity and audit

The six prepared reviewer-only ZIPs remain outside the frozen Git tree until all scores are submitted. No ZIP includes the answer-key JSON, comparison assignment, source `eval-...` IDs, or organizer report. All reviewer ZIPs contain a 20-row Excel scorecard, equivalent CSV, read-only JSONL and scoring guide.

A separate **organizer-only** ZIP contains the complete 120-case answer map, file checksums and `aggregate_reviews.py`, which refuses missing rows, invalid A/B/TIE values, scores outside 1–5, missing rationales, or tampered answer/prompt text. It only unmasks and aggregates after all six completed sheets are received.

The standard quality report must distinguish raw votes (60 per comparison), sample-level majorities (20 per comparison), reviewer disagreements and five-dimensional score differences. All paired analyses should recognize that there are **20 source prompts**, not 40 independent held-out prompts. The historical `ENGINEERING_PASS / QUALITY_PROMOTION_NOT_APPROVED` outcome remains unchanged unless a separate review is accepted as new supplementary evidence.

**Current outcome:** no independent reviewer has submitted a scored sheet. `EXTERNAL_GRADING_PENDING`; no claim of quality gain or review completion.

## Reviewer packages (SHA256 of ZIP bytes)

| Reviewer | ZIP SHA256 |
|---|---|
| R01 | `d6a968e72304d9d5e4a77271e779c508e2df79039300601346da44afedc4214d` |
| R02 | `19f03829fe2cd7bae17e468cc160b1adb15ac205d14e56525437e216369c8428` |
| R03 | `12409d28b71240372cfa7965d944c2b097cb23b57a3ce913c211b02b1491cad5` |
| R04 | `10c11a767d73058dde6a939354fb5f6ff645809a6570e64bac36d58145b5bf07` |
| R05 | `7a9b944402ef2f65222c9b324b39b9a25abc0feae53b9bc1e2557d79916a275e` |
| R06 | `899766af8674902891ff719a08b814d1718294994904a0493c29946a5fa83ade` |

These SHA256 values were verified against the six final ZIP files exported in the current conversation. Cross-check them with the organizer-only manifest before distribution. The organizer ZIP and its keys must never be given to judges.
