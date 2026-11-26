-- R58 target-time structural replay audit: aggregate SELECT only; no content/IDs emitted.
-- Replaying this query against live tables may change the cohort; source app code remains unverified.
-- R58 RolePlay v0.1 CHECKPOINT-AWARE PILOT: read-only metadata discovery only.
-- This SQL returns aggregate counts only; it does NOT return story/session/message IDs or body text.
-- Live analytics and session mutations mean reruns need not equal a frozen dataset.
WITH base AS MATERIALIZED (
 SELECT s.id,
 CASE WHEN jsonb_typeof(s.v2_data->'characters')='array' AND jsonb_array_length(s.v2_data->'characters')>1 THEN 'multi' ELSE 'single' END AS cb,
 CASE WHEN jsonb_typeof(s.v2_data->'world'->'timelineEvents')='array' AND jsonb_array_length(s.v2_data->'world'->'timelineEvents')>0 THEN 'timeline' ELSE 'no_timeline' END AS tb,
 CASE WHEN jsonb_typeof(s.v2_data->'director'->'npcs')='array' AND jsonb_array_length(s.v2_data->'director'->'npcs')>0 THEN 'npcs' ELSE 'no_npcs' END AS nb,
 a.assistant_completed
 FROM public.user_stories s JOIN public.analytics_story_lifetime a ON a.story_id=s.id
 WHERE s.deleted_at IS NULL AND s.story_type='v2_sandbox' AND s.source_type='original'
 AND s.moderation_status IN ('approved','override_approved') AND a.assistant_completed>=50
 AND EXISTS(SELECT 1 FROM public.story_content_versions v WHERE v.story_id=s.id)
 AND EXISTS(SELECT 1 FROM public.v2_session_checkpoints cp WHERE cp.story_id=s.id)
), ranked AS MATERIALIZED (
 SELECT *,row_number() OVER(PARTITION BY cb,tb,nb ORDER BY md5(id||':R58:20261030:pilot2:versioned')) AS rn FROM base
), pre AS MATERIALIZED (
 SELECT * FROM ranked WHERE rn<=15 ORDER BY rn,md5(id||':R58:20261030:pilot2:versioned') LIMIT 100
), sel AS MATERIALIZED (
 SELECT p.* FROM pre p WHERE EXISTS(SELECT 1 FROM public.story_v2_sessions se
 WHERE se.story_id=p.id AND se.deleted_at IS NULL AND se.materialization_status='ready'
 AND se.has_persisted_messages IS TRUE AND se.parent_session_id IS NULL AND se.total_turns>=15)
 ORDER BY rn,md5(p.id||':R58:20261030:pilot2:versioned') LIMIT 24
), picked_sessions AS MATERIALIZED (
 SELECT s.id AS story_id,ss.id AS session_pk,ss.user_id,ss.session_id FROM sel s
 JOIN LATERAL (SELECT se.id,se.user_id,se.session_id FROM public.story_v2_sessions se
 WHERE se.story_id=s.id AND se.deleted_at IS NULL AND se.materialization_status='ready'
 AND se.has_persisted_messages IS TRUE AND se.parent_session_id IS NULL AND se.total_turns>=15
 ORDER BY se.total_turns DESC,se.id LIMIT 2) ss ON TRUE
), target_slots AS MATERIALIZED (
 SELECT ps.story_id,ps.session_pk,mm.id AS message_pk FROM picked_sessions ps
 JOIN LATERAL (SELECT m.id FROM public.v2_chat_messages m
 WHERE m.story_id=ps.story_id AND m.session_id=ps.session_id AND m.user_id=ps.user_id
 AND m.role='assistant' AND m.status='completed' AND m.content IS NOT NULL AND m.turn_index>=2
 AND EXISTS (SELECT 1 FROM public.v2_session_checkpoints cp WHERE cp.session_id=m.session_id AND cp.story_id=m.story_id AND cp.user_id=m.user_id AND cp.created_at<=m.created_at AND cp.turn_index<=m.turn_index)
 ORDER BY m.turn_index DESC,m.created_at DESC,m.id LIMIT 3) mm ON TRUE
)
, targets AS MATERIALIZED (
 SELECT m.id,m.story_id,m.user_id,m.session_id,m.turn_index,m.created_at,m.content,m.mutation_revision,
 st.updated_at AS story_updated_at
 FROM target_slots t JOIN public.v2_chat_messages m ON m.id=t.message_pk
 JOIN public.user_stories st ON st.id=m.story_id
 WHERE EXISTS (SELECT 1 FROM public.story_content_versions v
  WHERE v.story_id=m.story_id AND v.source_updated_at<=m.created_at)
), investigated AS MATERIALIZED (
 SELECT t.id,t.mutation_revision,
 EXISTS(SELECT 1 FROM public.story_content_versions v WHERE v.story_id=t.story_id
  AND v.source_updated_at<=t.created_at AND v.archived_at>t.created_at) AS archive_interval,
 t.story_updated_at<=t.created_at AS current_story_before,
 cp.snapshot_version,cp.gap,cp.has_director,cp.has_facts,cp.has_event_runtime,
 cp.has_summary,cp.has_system,cp.has_messages,
 led.has_before_image,led.content_changed_prior
 FROM targets t
 LEFT JOIN LATERAL (
  SELECT c.snapshot_version,(t.turn_index/2-c.turn_index) AS gap,
   c.snapshot ? 'director_state' AS has_director,
   c.snapshot ? 'memory_facts' AS has_facts,
   c.snapshot ? 'event_runtime' AS has_event_runtime,
   c.snapshot ? 'summary_source_end_index' AS has_summary,
   c.snapshot ? 'full_system_prompt' AS has_system,
   c.snapshot ? 'messages' AS has_messages
  FROM public.v2_session_checkpoints c
  WHERE c.session_id=t.session_id AND c.story_id=t.story_id AND c.user_id=t.user_id
   AND c.created_at<=t.created_at AND c.turn_index*2<t.turn_index
  ORDER BY c.turn_index DESC,c.created_at DESC LIMIT 1
 )cp ON TRUE
 LEFT JOIN LATERAL (
  SELECT count(*) FILTER(WHERE l.operation='update_before')>0 AS has_before_image,
   coalesce(bool_or(l.operation='update_before' AND l.row_data->>'content' IS DISTINCT FROM t.content),false) AS content_changed_prior
  FROM public.v2_chat_message_ledger l
  WHERE l.session_id=t.session_id AND l.story_id=t.story_id AND l.user_id=t.user_id AND l.message_id=t.id
 )led ON TRUE
)
SELECT count(*) AS early_version_source_targets,
 count(*) FILTER(WHERE archive_interval) AS archived_valid_interval,
 count(*) FILTER(WHERE NOT archive_interval AND current_story_before) AS current_timestamp_consistent,
 count(*) FILTER(WHERE NOT archive_interval AND NOT current_story_before) AS story_version_hold,
 count(*) FILTER(WHERE snapshot_version=2) AS prior_checkpoint_v2,
 count(*) FILTER(WHERE gap<=5) AS cp_gap_le5,
 count(*) FILTER(WHERE gap<=20) AS cp_gap_le20,
 count(*) FILTER(WHERE gap>50) AS cp_gap_gt50,
 count(*) FILTER(WHERE has_director) AS cp_director_state,
 count(*) FILTER(WHERE has_facts) AS cp_memory_facts,
 count(*) FILTER(WHERE has_event_runtime) AS cp_event_runtime,
 count(*) FILTER(WHERE has_summary) AS cp_summary_cursor,
 count(*) FILTER(WHERE has_system) AS cp_full_system_prompt,
 count(*) FILTER(WHERE has_messages) AS cp_full_messages,
 count(*) FILTER(WHERE has_before_image) AS ledger_with_before_image,
 count(*) FILTER(WHERE content_changed_prior) AS ledger_historical_content_divergence,
 count(*) FILTER(WHERE mutation_revision>0) AS target_mutation_revision_positive
FROM investigated;