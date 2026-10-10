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
| R01 | `5fd21c25c14468d5eb51187b4477d5e22f02b0b55483a9dfaa977f11222a2269` |
| R02 | `57b0091f31d9e90dc25569f29840189634d283f926f028c606b734e15e45dba9` |
| R03 | `1c4d5ed74cd85c16730570d4a8262b1b4d7d3dc57be42e0bf82704f9018e6f5a` |
| R04 | `35bcb1cbe0b9c6a3b2bd708f3e709f53dfc95123862aa0bcf3a61d3df27fa268` |
| R05 | `d536fca893a7fa2e59e42b6f0a629ce767e338c88e6ef3a67b130e54703d54c6` |
| R06 | `64b84d989230ac42701adcd2fbdcbf8d254842c97ff94320ef4b45c0e71f7758` |

Verify real archive digests against organizer-only manifest before distribution; listed checksums are provisional until matched to the exact final exported files. The organizer ZIP and its keys must never be given to judges.
