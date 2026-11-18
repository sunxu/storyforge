-- REVIEW ONLY: Owner must inspect and apply manually in Supabase SQL Editor.
-- Scope: R60 Base336 P2 public-original source metadata only.
-- No grants, role changes, table changes, or data writes are performed here.
-- Requires existing SELECT grants to r58_export_reader and existing RLS on both tables.
-- This policy intentionally exposes only current-revision moderation rows and
-- permission events tied to those current-revision public submissions.
--
-- The policy predicate mirrors the P2 public source selector. It does not grant
-- training, redistribution, or access to private chat/session tables.

BEGIN;

CREATE POLICY r58_export_reader_p2_current_public_submissions_select
ON public.story_moderation_submissions
AS PERMISSIVE
FOR SELECT
TO r58_export_reader
USING (
    requested_visibility = 'public'
    AND EXISTS (
        SELECT 1
        FROM public.user_stories us
        WHERE us.id = story_moderation_submissions.story_id::text
          AND us.public_content_revision = story_moderation_submissions.content_revision
          AND us.visibility = 'public'
          AND us.status = 'published'
          AND us.deleted_at IS NULL
          AND us.moderation_state IN ('ai_approved', 'human_approved')
          AND us.source_type = 'original'
          AND us.created_at >= TIMESTAMPTZ '2026-11-16 02:03:25+00'
          AND us.public_v2_data->>'cardType' = 'story'
          AND us.public_v2_data->'opening'->>'originality' = 'original'
          AND us.public_v2_data->'opening'->>'visibility' = '公开'
          AND length(us.public_v2_data->'world'->>'worldSentence') > 5
    )
);

CREATE POLICY r58_export_reader_p2_current_public_permission_events_select
ON public.story_permission_events
AS PERMISSIVE
FOR SELECT
TO r58_export_reader
USING (
    submission_id IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.story_moderation_submissions sm
        JOIN public.user_stories us
          ON us.id = sm.story_id::text
        WHERE sm.id = story_permission_events.submission_id
          AND sm.story_id::text = story_permission_events.story_id
          AND sm.content_revision = us.public_content_revision
          AND sm.requested_visibility = 'public'
          AND us.visibility = 'public'
          AND us.status = 'published'
          AND us.deleted_at IS NULL
          AND us.moderation_state IN ('ai_approved', 'human_approved')
          AND us.source_type = 'original'
          AND us.created_at >= TIMESTAMPTZ '2026-11-16 02:03:25+00'
          AND us.public_v2_data->>'cardType' = 'story'
          AND us.public_v2_data->'opening'->>'originality' = 'original'
          AND us.public_v2_data->'opening'->>'visibility' = '公开'
          AND length(us.public_v2_data->'world'->>'worldSentence') > 5
    )
);

COMMIT;
