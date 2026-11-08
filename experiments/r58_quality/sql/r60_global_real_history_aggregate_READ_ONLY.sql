-- StoryForge R60 REAL-01: global authorized metadata DISCOVERY only.
-- Executed against existing ChatGPT read-only connector (not r58_export_reader).
-- Never select user content, metadata JSONB values, IDs, credential fields or raw text.
-- DO NOT reuse output as Quality-v1, consent, rights or R50 PASS.
-- User authorized all story_id/session_id for G0 technical discovery on 2026-11-08.
-- Query bounds: four cohorts x 16 distinct stories x 20 completed assistant = <=1280 rows.
WITH roots AS MATERIALIZED (
 SELECT DISTINCT ON (st.source_type, st.visibility, s.story_id)
  st.source_type, st.visibility, s.story_id, s.session_id, s.total_turns
 FROM public.story_v2_sessions s
 JOIN public.user_stories st ON st.id = s.story_id
 WHERE st.status = 'published'
   AND st.deleted_at IS NULL
   AND s.deleted_at IS NULL
   AND s.is_archived = false
   AND s.total_turns >= 50
   AND (
     (st.source_type = 'original' AND st.visibility IN ('public', 'private'))
     OR (st.source_type IN ('ai_assisted', 'dice_cocreate')
         AND st.visibility = 'public')
   )
 ORDER BY st.source_type, st.visibility, s.story_id,
          s.total_turns DESC, s.session_id
), ranked AS MATERIALIZED (
 SELECT source_type, visibility, story_id, session_id,
        row_number() OVER (
          PARTITION BY source_type, visibility ORDER BY md5(story_id)
        ) AS ordinal
 FROM roots
), sampled AS MATERIALIZED (
 SELECT source_type, visibility, story_id, session_id
 FROM ranked WHERE ordinal <= 16
), replies AS MATERIALIZED (
 SELECT sc.source_type, sc.visibility, m.story_id, m.session_id,
        m.turn_index, m.metadata,
        char_length(m.content) AS target_chars
 FROM sampled sc
 CROSS JOIN LATERAL (
  SELECT story_id, session_id, turn_index, metadata, content
  FROM public.v2_chat_messages
  WHERE session_id = sc.session_id AND story_id = sc.story_id
    AND role = 'assistant' AND status = 'completed'
  ORDER BY turn_index DESC LIMIT 20
 ) m
)
SELECT sc.source_type, sc.visibility,
 count(DISTINCT sc.story_id)::int AS scoped_stories,
 count(DISTINCT sc.session_id)::int AS scoped_sessions,
 count(r.turn_index)::int AS assistant_completed,
 count(*) FILTER (
   WHERE u.role='user' AND u.status='completed' AND u.story_id=r.story_id
 )::int AS adjacent_completed,
 count(*) FILTER (
   WHERE u.role='user' AND u.status='completed' AND u.story_id=r.story_id
     AND r.target_chars >= 300
 )::int AS adjacent_300plus,
 count(*) FILTER (
   WHERE u.role='user' AND u.status='completed' AND u.story_id=r.story_id
     AND r.target_chars >= 300
     AND r.metadata->>'finishReason' IN ('stop','STOP','end_turn','END_TURN')
     AND NOT (r.metadata ? 'originalContent' OR r.metadata ? 'editedAt')
     AND NOT (r.metadata ? 'parseWarnings')
 )::int AS priority,
 count(DISTINCT r.story_id) FILTER (
   WHERE u.role='user' AND u.status='completed' AND u.story_id=r.story_id
     AND r.target_chars >= 300
     AND r.metadata->>'finishReason' IN ('stop','STOP','end_turn','END_TURN')
     AND NOT (r.metadata ? 'originalContent' OR r.metadata ? 'editedAt')
     AND NOT (r.metadata ? 'parseWarnings')
 )::int AS priority_stories
FROM sampled sc
LEFT JOIN replies r ON r.session_id=sc.session_id AND r.story_id=sc.story_id
LEFT JOIN public.v2_chat_messages u
  ON u.session_id=r.session_id AND u.turn_index=r.turn_index-1
GROUP BY sc.source_type,sc.visibility
ORDER BY sc.source_type,sc.visibility;
