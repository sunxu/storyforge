-- R60-REAL-04 / R60-REAL-01: author-played original/private cohort.
-- 2026-11-08 owner authorization: global story/session *metadata-only* discovery.
-- This query is a bounded aggregate, never outputs or loads message content to client.
-- "author plays own story" DOES NOT establish consent, training rights, privacy,
-- third-party rights, historical world version, or Test-set nonoverlap.
-- No literal Story ID/User ID/Session ID may be returned or copied to GitHub.

WITH candidate_sessions AS MATERIALIZED (
  SELECT DISTINCT ON (s.story_id)
     s.story_id, s.session_id, s.total_turns
  FROM public.story_v2_sessions s
  JOIN public.user_stories st ON st.id=s.story_id
  WHERE st.status='published' AND st.deleted_at IS NULL
    AND st.source_type='original' AND st.visibility='private'
    AND s.deleted_at IS NULL AND s.is_archived=false
    AND s.user_id=st.author_id AND s.total_turns>=30
  ORDER BY s.story_id,s.total_turns DESC,s.session_id
), sampled AS MATERIALIZED (
  SELECT story_id, session_id FROM candidate_sessions
  ORDER BY md5(story_id) LIMIT 16
), replies AS MATERIALIZED (
  SELECT m.story_id,m.session_id,m.turn_index,m.metadata,
         char_length(m.content) AS target_chars
  FROM sampled c
  CROSS JOIN LATERAL (
    SELECT story_id,session_id,turn_index,metadata,content
    FROM public.v2_chat_messages
    WHERE story_id=c.story_id AND session_id=c.session_id
      AND role='assistant' AND status='completed'
    ORDER BY turn_index DESC LIMIT 20
  ) m
)
SELECT count(DISTINCT s.story_id)::int AS sampled_stories,
 count(DISTINCT s.session_id)::int AS sampled_sessions,
 count(r.turn_index)::int AS completed_targets,
 count(*) FILTER (
   WHERE u.role='user' AND u.status='completed' AND u.story_id=r.story_id
 )::int AS adjacent_completed,
 count(*) FILTER (
   WHERE u.role='user' AND u.status='completed' AND u.story_id=r.story_id
     AND r.target_chars>=300
 )::int AS length300,
 count(*) FILTER (
   WHERE u.role='user' AND u.status='completed' AND u.story_id=r.story_id
     AND r.target_chars>=300
     AND r.metadata->>'finishReason' IN ('stop','STOP','end_turn','END_TURN')
     AND NOT (r.metadata ? 'originalContent' OR r.metadata ? 'editedAt')
     AND NOT (r.metadata ? 'parseWarnings')
 )::int AS technical_priority,
 count(DISTINCT r.story_id) FILTER (
   WHERE u.role='user' AND u.status='completed' AND u.story_id=r.story_id
     AND r.target_chars>=300
     AND r.metadata->>'finishReason' IN ('stop','STOP','end_turn','END_TURN')
     AND NOT (r.metadata ? 'originalContent' OR r.metadata ? 'editedAt')
     AND NOT (r.metadata ? 'parseWarnings')
 )::int AS priority_stories
FROM sampled s
LEFT JOIN replies r ON r.story_id=s.story_id AND r.session_id=s.session_id
LEFT JOIN public.v2_chat_messages u
 ON u.session_id=r.session_id AND u.turn_index=r.turn_index-1;
