-- R60-REAL-02: bounded G1 preview of real historical User / Assistant text.
-- Owner instruction (2026-11-08): use R60 real historical data for training
-- pipeline; stop further contract/rights investigations.
-- NEVER copy query result text or any user/story/session ID to GitHub, issue
-- discussions, public logs, or CI. Review in approved private environment only.
-- No database modification, no R50 protected-set body, no current Story Draft.
-- Outputs up to six stories, one candidate per story. Not a dataset export.
-- Reproducibility depends on the live database snapshot; persist exact locators
-- ONLY in Owner-local private 0700/0600 storage for subsequent double-review.
-- Target = DB_FINAL_PERSISTED_ASSISTANT, NOT original provider stream/delivered UI.
-- The historical system/world snapshot is unknown; do not fabricate it.
WITH eligible AS MATERIALIZED (
  SELECT DISTINCT ON (s.story_id) s.story_id, s.session_id, s.total_turns
  FROM public.story_v2_sessions s
  JOIN public.user_stories st ON st.id = s.story_id
  WHERE st.status='published' AND st.deleted_at IS NULL
    AND st.source_type='original' AND st.visibility='private'
    AND s.deleted_at IS NULL AND s.is_archived=false
    AND s.user_id=st.author_id AND s.total_turns>=30
  ORDER BY s.story_id,s.total_turns DESC,s.session_id
), sampled AS MATERIALIZED (
  SELECT story_id,session_id FROM eligible ORDER BY md5(story_id) LIMIT 16
), replies AS MATERIALIZED (
  SELECT c.story_id,c.session_id,m.turn_index,m.content AS assistant_text,
         m.metadata,char_length(m.content) AS target_chars
  FROM sampled c
  CROSS JOIN LATERAL (
    SELECT turn_index,content,metadata
    FROM public.v2_chat_messages
    WHERE story_id=c.story_id AND session_id=c.session_id
      AND role='assistant' AND status='completed'
    ORDER BY turn_index DESC LIMIT 20
  ) m
), qualified AS (
  SELECT r.*,u.content AS user_text,
         p.content AS previous_assistant_text,
         pu.content AS previous_user_text,
         row_number() OVER (PARTITION BY r.story_id ORDER BY r.turn_index DESC) AS story_rank
  FROM replies r
  JOIN public.v2_chat_messages u
    ON u.story_id=r.story_id AND u.session_id=r.session_id
   AND u.turn_index=r.turn_index-1
   AND u.role='user' AND u.status='completed'
  LEFT JOIN public.v2_chat_messages p
    ON p.story_id=r.story_id AND p.session_id=r.session_id
   AND p.turn_index=r.turn_index-2
   AND p.role='assistant' AND p.status='completed'
  LEFT JOIN public.v2_chat_messages pu
    ON pu.story_id=r.story_id AND pu.session_id=r.session_id
   AND pu.turn_index=r.turn_index-3
   AND pu.role='user' AND pu.status='completed'
  WHERE r.target_chars BETWEEN 300 AND 1500
    AND r.metadata->>'finishReason' IN ('stop','STOP','end_turn','END_TURN')
    AND NOT (
      r.metadata ? 'originalContent'
      OR r.metadata ? 'editedAt'
      OR r.metadata ? 'parseWarnings'
    )
    AND char_length(u.content) BETWEEN 1 AND 800
    AND (p.content IS NULL OR char_length(p.content)<=1800)
    AND (pu.content IS NULL OR char_length(pu.content)<=800)
)
SELECT row_number() OVER (ORDER BY story_id)::int AS review_no,
       target_chars,char_length(user_text)::int AS user_chars,
       previous_user_text,previous_assistant_text,user_text,assistant_text,
       'DB_FINAL_PERSISTED_ASSISTANT'::text AS target_semantics,
       'UNVERIFIED_HISTORICAL_SYSTEM'::text AS system_state
FROM qualified
WHERE story_rank=1
ORDER BY story_id
LIMIT 6;
