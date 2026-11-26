-- PRIVATE: 只读导出经 Owner 批准的单一训练会话。**不要直接运行占位符**。
-- 仅限已分到 TRAIN 候选池的故事与会话；R50、潜在 Held-out 世界禁止执行。
-- 在参数化客户端绑定 :approved_story_id、:approved_session_id、:approved_user_id。
-- 必须先确认分支 parent_session_id / forked_from_turn 及历史继承策略。
-- 不得把本查询返回的内容直接粘贴到聊天、普通 GitHub 或 SAFE 归档。
SELECT
  m.id::text AS message_id,
  m.story_id,
  m.session_id,
  m.role,
  m.turn_index,
  m.status,
  m.mutation_revision,
  m.created_at,
  m.content,
  m.metadata
FROM public.v2_chat_messages m
WHERE m.story_id = :approved_story_id
  AND m.session_id = :approved_session_id
  AND m.user_id = :approved_user_id
ORDER BY m.turn_index, m.created_at, m.id
LIMIT 2000;
-- 当前故事配置和 Session 状态需分别获取，但不能假定它们等同目标时点快照。
