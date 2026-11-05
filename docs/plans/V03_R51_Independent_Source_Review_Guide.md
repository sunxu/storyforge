# StoryForge R51 — Two independent reviewers (private Gold108)

**Task:** For each review case, independently judge whether the exact, frozen
visible messages support the original Assistant target *without* unverified
story/persona/system cards or facts that appear only in source history outside
the frozen visible input. The project owner has already confirmed general
age/consent/content boundaries; do not repeatedly demand that generic
confirmation. Rights to train on the source remain a distinct approval gate.

**Privacy:** All JSONL tasks include private original chat dialogue and
message IDs. They are created locally in mode-0600 files, not committed,
included in CI logs, or posted to a public service. The owner chooses whether
and how to deliver a task file to a qualified independent reviewer. Reviewers
must not access each other's responses, R47/R48 results or R50 sealed test
materials. No model training or test unsealing is authorized.

## Bounded first batch

```bash
cd ~/workspace/storyforge
git pull --ff-only
install -d -m 700 ~/.local/share/storyforge/r51/reviews

python3 scripts/v03_r51_independent_source_reviews.py \
  --prepare --private-packets \
  ~/.local/share/storyforge/r51/R51_GOLD108_PRIVATE_CONTEXT_REVIEW_v1.jsonl \
  --out-dir ~/.local/share/storyforge/r51/reviews --batch 1
```

Creates *two* isolated 24-case tasks for reviewers A/B (same cases,
independently ordered). Batches 2–4 have 24 each, batch 5 has 12;
together they cover 108 distinct Gold108 records. Do not copy the
result files between reviewers. For each batch, each reviewer sends
one JSONL record per candidate with this literal result schema:

```json
{
  "schema": "storyforge-r51-independent-context-review-result-v1",
  "reviewer": "A",
  "batch_number": 1,
  "candidate_id": "COPY_FROM_TASK",
  "target_sha256": "COPY_FROM_TASK",
  "route": "CONTEXT_ONLY_POSSIBLE__HOLD",
  "source_citations": [
    {
      "scope": "FROZEN_VISIBLE",
      "original_source_array_index": 123,
      "source_body_sha256": "COPY_FROM_VISIBLE_MESSAGE"
    },
    {
      "scope": "TARGET",
      "original_source_array_index": 124,
      "source_body_sha256": "COPY_TASK_TARGET_SHA256"
    }
  ],
  "rationale": "Explain which required premises are actually visible, and any missing rules/facts.",
  "training_admission": "PENDING_NOT_APPROVED"
}
```

The example integers and names are placeholders, not real source references.
Reviewer B must use `"reviewer": "B"`. Both must choose exactly one of:

- `CONTEXT_ONLY_POSSIBLE__HOLD`: every premise required for the target
  is supported inside the frozen visible history. Requires at least one
  `FROZEN_VISIBLE` and one `TARGET` source citation.
- `CARD_OR_LONG_RANGE_SOURCE_REQUIRED__HOLD`: the target uses facts/rules
  missing from frozen visible history; identify the dependency in rationale
  and cite the closest real source or relevant target.
- `INSUFFICIENT_VISIBLE_CONTEXT__HOLD`: available excerpts do not allow
  a grounded determination; never infer missing facts from a current export card.
- `TARGET_AGENCY_OR_RULE_CONCERN__HOLD`: original Assistant target appears
  to insert player dialogue/psychology/choices or violate a known instruction.
  Distinguish defects in earlier, unsupervised dialogue from the target itself.

The four preceding source messages, if supplied, are *reviewer-only*.
If they establish facts absent from frozen visible input, they are evidence
of **missing context**, not permission to silently add them as a new model
input. A review packet is not a full story/card source: if uncertain about
a long-range rule, use a HOLD verdict and request deeper original-source
inspection. Neither reviewer can approve Train/Val or certify rights.

Save complete separate private files
`R51_BATCH_01_REVIEWER_A_RESULTS.jsonl` and
`R51_BATCH_01_REVIEWER_B_RESULTS.jsonl` under the same protected directory.

Once both are complete, validate source references and produce a strictly
private reconciliation:

```bash
python3 scripts/v03_r51_independent_source_reviews.py \
  --reconcile --batch 1 \
  --private-packets \
  ~/.local/share/storyforge/r51/R51_GOLD108_PRIVATE_CONTEXT_REVIEW_v1.jsonl \
  --out-dir ~/.local/share/storyforge/r51/reviews \
  --review-A ~/.local/share/storyforge/r51/reviews/R51_BATCH_01_REVIEWER_A_RESULTS.jsonl \
  --review-B ~/.local/share/storyforge/r51/reviews/R51_BATCH_01_REVIEWER_B_RESULTS.jsonl
```

The validator checks case coverage, source SHA citations, reviewer identity,
target SHA, independent route fields and non-admission. It reports only
counts; mismatched independent reviewers remain HOLD for adjudication.
Route agreement is **not training admission**: age/owner statement is
separate from rights, actual forbidden rules, complete world/alias
isolation, R50 boundary and ms-swift model-input checks. Repeat with
`--batch 2` through `--batch 5` after reviewing batch 1.
