-- R60-REAL P0: policy-date coverage check for author-played original/private sessions.
-- G0 metadata-only; no message text, user/story/session IDs, or individual timestamps returned.
-- Page dates are comparison cutoffs, NOT proof of policy effectiveness or user acceptance.
-- Live production data can drift. Never treat this query as G1/G2 authorization.
WITH eligible AS MATERIALIZED (
  SELECT s.story_id, s.created_at, s.last_message_at
  FROM public.story_v2_sessions s
  JOIN public.user_stories st ON st.id = s.story_id
  WHERE st.status = 'published'
    AND st.deleted_at IS NULL
    AND st.source_type = 'original'
    AND st.visibility = 'private'
    AND s.deleted_at IS NULL
    AND s.is_archived = false
    AND s.user_id = st.author_id
    AND s.total_turns >= 30
)
SELECT
  count(*)::int AS total_sessions,
  count(DISTINCT story_id)::int AS distinct_stories,
  count(*) FILTER (
    WHERE created_at < TIMESTAMPTZ '2026-01-12 00:00:00+00'
  )::int AS session_created_before_privacy_page_date,
  count(*) FILTER (
    WHERE created_at >= TIMESTAMPTZ '2026-01-12 00:00:00+00'
      AND created_at < TIMESTAMPTZ '2026-09-24 00:00:00+00'
  )::int AS session_created_between_page_dates,
  count(*) FILTER (
    WHERE created_at >= TIMESTAMPTZ '2026-09-24 00:00:00+00'
  )::int AS session_created_on_or_after_terms_page_date,
  count(*) FILTER (WHERE created_at IS NULL)::int AS session_created_null,
  count(*) FILTER (WHERE last_message_at IS NULL)::int AS last_message_null
FROM eligible;
