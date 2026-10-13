# Source evidence contract — target-time story/persona/system prompt

To resolve this R02 gate, collect evidence **bound to each target Assistant message ID and generation request**. Do not substitute export-time `story.v2_data`, session summary, event-runtime metadata or a manually rewritten card.

## Preferred provenance

1. **Original generation request**, with immutable request/target IDs, the exact system prompt bytes (or encrypted evidence object with SHA256), captured source timestamp and content hashes.
2. **Immutable card revision history + prompt composition record**, with revision ID, effective-from / effective-to, revision bytes/hash, request trace ID, model/template identity and the mapping proving the historical request used that revision.

Suggested record fields:
`candidate_id`, `source_story_id`, `target_message_id`, `target_created_at`, `request_trace_id`, `evidence_kind`, `evidence_sha256`, `system_prompt_sha256`, `asof_revision_id`, `revision_effective_from`, `revision_effective_to`, `template_version`, `source_transaction_ref`, `reviewer`, `review_decision`.

A structural check cannot cryptographically prove historical truth without genuine source artifacts. Time order alone, including `story.updated_at <= target.created_at`, is not sufficient.

## Additional independent gates

- Establish all applicable participant/player/NPC ages, authorized relationships and content boundaries **at the target time**. Export-time age literals do not approve the sample.
- Respect the 04↔07 linked-world isolation issue; 07 has zero selected candidates in this cohort but is not universally cleared.
- Freeze future train/validation/test boundaries by independent story and linked story group, accounting for first-cohort overlaps with v0.1 Train.
- Then use the exact as-of system prompt with a **pinned** Qwen tokenizer/chat template to check 16,384 tokens, followed by actual ms-swift last-round `labels` on every training/validation sample.

Raw prompts, identities and full conversations should remain in private protected evidence storage. The Git audit index should contain hashes and IDs, not sensitive prompt or story body. Do not fabricate missing versions.
