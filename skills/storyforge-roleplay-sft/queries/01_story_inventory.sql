-- 只读元数据与存量统计。不选取正文或任何个人数据。
SHOW transaction_read_only;
SELECT COUNT(*) AS stories,
       COUNT(*) FILTER (WHERE deleted_at IS NULL) AS not_deleted,
       COUNT(*) FILTER (WHERE story_type = 'v2_sandbox') AS v2_sandbox,
       COUNT(*) FILTER (WHERE deleted_at IS NULL AND moderation_status IN ('approved', 'override_approved')) AS approved_active
FROM public.user_stories;

SELECT COUNT(*) AS sessions,
       COUNT(*) FILTER (WHERE deleted_at IS NULL) AS active_sessions,
       COUNT(*) FILTER (WHERE parent_session_id IS NOT NULL) AS fork_sessions,
       COUNT(*) FILTER (WHERE total_turns >= 10) AS sessions_10plus,
       COUNT(*) FILTER (WHERE materialization_status = 'ready') AS ready_sessions
FROM public.story_v2_sessions;

SELECT COUNT(*) AS analytics_world_rows,
       SUM(assistant_completed) AS completed_assistant_rollup,
       MAX(refreshed_at) AS newest_rollup
FROM public.analytics_story_lifetime;
