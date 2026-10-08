# Dataset v0.1 contract

StoryForge keeps the exported source archive immutable and compiles it into model-ready JSONL.

## Raw record types

The 2026-09-30 export contains: `story_metadata`, `story_card`, `session`, `opening` / `opening_candidates`, `message`, and `non_content_message`.

Only `message` records participate directly in SFT dialogue construction.

## Training target

A training sample is created for every assistant `message` with `is_selected=true`.
The nearest preceding user message in the same transcript is the current user turn.

## Leakage rule

For a selected assistant target at sequence N:

- input history may contain message content with sequence < N
- the current user message is included
- the selected assistant content is the only supervised target
- target-message metadata is NEVER rendered into the prompt
- records after sequence N are NEVER visible to the sample
- `non_content_message` records are excluded from dialogue

Past assistant message content may contain state/status text because it was already visible before the target turn. Hidden metadata is not injected.

## Story card selection

Prefer the exact `story_card_version_id` referenced by the target message. If unavailable, fall back to the session-referenced card, then the latest available card. The chosen version is recorded in sample metadata.

## Opening

Use only an opening explicitly associated with the transcript/session. If opening selection is unresolved (`opening_candidates`), omit opening content and record the uncertainty in metadata.

## Context window

Dataset v0.1 keeps the latest N dialogue messages before the target (default: 12 messages / roughly 6 turns). Earlier dialogue is not silently summarized in v0.1.

A later dataset version may add deterministic summaries, but summaries must be generated only from pre-target history.

## Split isolation

Train/validation/test are split by `story_id`, never by individual sample. This prevents the same story/character card from leaking across splits.

For 19 stories, v0.1 defaults to 15 stories train, 2 stories validation, and 2 stories test. The assignment is deterministic from SHA-256 ordering of `story_id`.

## Compiled JSONL shape

```json
{
  "id": "sample-000001",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "metadata": {
    "story_id": "...",
    "transcript_id": "...",
    "target_message_id": "...",
    "source_sample_ids": [1],
    "story_card_version_id": "...",
    "opening_status": "...",
    "context_message_count": 12
  }
}
```

The final assistant message is the supervised target.
