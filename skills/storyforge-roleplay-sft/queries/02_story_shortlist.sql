-- 返回无对话正文、无 user_id 的私有候选目录。
-- SQL 编辑器导出 CSV 后保存于 HF 私有区域；story_id 不能写普通 Git。
-- assistant_completed 来自近实时物化汇总，不等于有效 Gold 数量。
SELECT
  s.id AS story_id,
  s.genre,
  s.source_type,
  s.moderation_status,
  s.story_type,
  (s.deleted_at IS NULL) AS not_deleted,
  (s.v2_data ? 'world') AS has_world,
  (s.v2_data ? 'character') AS has_character,
  (s.v2_data ? 'director') AS has_director,
  (s.v2_data ? 'opening') AS has_opening,
  (CASE WHEN jsonb_typeof(s.v2_data->'characters') = 'array'
    THEN jsonb_array_length(s.v2_data->'characters') > 0 ELSE FALSE END) AS has_characters,
  COALESCE(a.assistant_completed, 0) AS assistant_completed,
  COALESCE(a.total_sessions, 0) AS session_count,
  a.refreshed_at AS analytics_refreshed_at
FROM public.user_stories s
LEFT JOIN public.analytics_story_lifetime a ON a.story_id = s.id
WHERE s.deleted_at IS NULL
  AND s.story_type = 'v2_sandbox'
  AND s.moderation_status IN ('approved','override_approved')
  AND COALESCE(a.assistant_completed, 0) >= 50
ORDER BY a.assistant_completed DESC, s.id
LIMIT 2000;
