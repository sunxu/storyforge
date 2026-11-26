# StoryForge R50 — Private case provenance preflight

Date: 2026-10-15. Status: DRAFT — pending independent test inputs, manual source/alias review and frozen R45 originals. No GPU or release approval.

## Private inputs

An independent author provides 40–60 newly authored prompt-only cases (4+ separate worlds), conforming to the earlier intake kit: case_id, world_id, world_card, long_term_rules, history, user_input, optional focus_tags. The author must not use earlier R47/R48 answers or scores. No Gold targets or reviewer ratings.

The coordinator separately provides one PRIVATE case_provenance.jsonl row per case with exactly:
case_id, story_number (16–20), source_story_id, source_session_id, cutoff_message_id, history_message_ids (nonempty, consecutive source message IDs ending with cutoff), and card_evidence (object with kind and record_id). Valid card_evidence kinds: export_time_card, content_versions, moderation_source_snapshots.

This mapping contains source-specific references and must not be committed to Git. The sample number, history message content, source IDs and historical card revision must be read from canonical source data, never guessed. The new player input must be independently authored, not a replay of the source transcript.

## Offline command

Run from the Git audit/r49-r50-source-intake-20261015 branch, with full source files available:

    python3 scripts/v03_r50_case_provenance.py \
      --repo . \
      --receipt docs/evidence/V03_R50_SOURCE_16_20_RECEIPT_20261015.json \
      --inputs /secure/r50/canonical_inputs.jsonl \
      --provenance /secure/r50/case_provenance.jsonl \
      --output /secure/r50/R50_CASE_PROVENANCE_REPORT.json

Full prompt JSONL, provenance and output must all reside OUTSIDE the repository. Output is aggregate-only, exclusive-create, mode 0600. First run the separate existing intake_seal.py schema/decontamination workflow; this source-cutoff tool is complementary.

The tool verifies all 35 Git source files' receipt, stable story/session identity, card evidence time before cutoff, exact immutable original historical messages, chronological ordering and duplicate source-player-input protection. Passing is only SOURCE_CUTOFF_AND_VERBATIM_HISTORY_PASS__SEMANTIC_REVIEW_PENDING.

Still mandatory: verify original PRIVATE R45 Train49/Val15 inputs, independently review character/world aliases and cutoff-specific world facts, human author independence, rights/content, final SHA256 seal and owner-approved preregistration. No real new tests have been received and no paid inference may start.

Marker: R50_CASE_PROVENANCE_TOOL_TESTED__NEW_INPUT_PENDING__NO_GPU.
