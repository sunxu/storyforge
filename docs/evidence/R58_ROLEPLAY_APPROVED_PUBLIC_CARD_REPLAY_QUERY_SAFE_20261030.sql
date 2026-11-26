-- StoryForge R58: historical approved public-card provenance, SAFE aggregate-only / SELECT-only.
-- RolePlay code pin: sunxu/RolePlay e9fe29c42434caeb0bac5acc91845ab4741ecb2b.
-- Approved projection trigger: maintain_story_public_version_projection.
-- No story IDs, user IDs, character cards, messages or JSON source bodies leave SQL.
-- All counts reflect LIVE database query and do not freeze the physical target list.
-- R58 RolePlay source-aware audit, SELECT-only, aggregate-only, no IDs/texts/prompt bodies emitted.
-- The results apply only to the pinned 2026-10-30 pilot cohort and live database query time.
-- Repo analysis pinned: sunxu/RolePlay e9fe29c42434caeb0bac5acc91845ab4741ecb2b.
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
, candidates AS MATERIALIZED (
 SELECT m.id,m.story_id,m.user_id,m.session_id,m.created_at,m.platform,m.turn_index,m.metadata,m.mutation_revision,
        s.author_id,s.public_content_revision,s.public_updated_at,s.public_v2_data,s.updated_at AS story_updated_at,
        EXISTS(SELECT 1 FROM public.story_content_versions v
          WHERE v.story_id=m.story_id AND v.source_updated_at<=m.created_at AND v.archived_at>m.created_at
        ) AS archived_interval
 FROM target_slots t JOIN public.v2_chat_messages m ON m.id=t.message_pk
 JOIN public.user_stories s ON s.id=m.story_id
 WHERE EXISTS(SELECT 1 FROM public.story_content_versions v
               WHERE v.story_id=m.story_id AND v.source_updated_at<=m.created_at)
)
, approved AS MATERIALIZED (
 SELECT c.id,c.story_id,c.user_id,c.author_id,c.created_at,c.public_updated_at,c.public_v2_data,c.story_updated_at,
  decision.submission_id,decision.approved_at,
  sub.content_revision,sub.snapshot->'source'->'v2Data' AS approved_story_v2data
 FROM candidates c LEFT JOIN LATERAL (
  SELECT a.submission_id,a.created_at AS approved_at
  FROM public.story_moderation_action_logs a
  WHERE a.story_id::text=c.story_id AND a.created_at<c.created_at
    AND a.to_state IN ('ai_approved','human_approved') AND a.to_visibility='public'
  ORDER BY a.created_at DESC,a.id DESC LIMIT 1
 ) decision ON TRUE
 LEFT JOIN public.story_moderation_submissions sub ON sub.id=decision.submission_id
)
SELECT
 CASE WHEN user_id=author_id THEN 'AUTHOR_DRAFT'
      WHEN public_updated_at<=created_at THEN 'READER_CURRENT_APPROVED'
      ELSE 'READER_PREVIOUS_APPROVED' END AS cohort,
 count(*) AS target_positions,
 count(*) FILTER (WHERE submission_id IS NOT NULL) AS prior_approval_action,
 count(*) FILTER (WHERE jsonb_typeof(approved_story_v2data)='object') AS approved_full_v2_data_present,
 count(*) FILTER (WHERE approved_story_v2data=public_v2_data) AS equals_current_public_v2_data,
 count(*) FILTER (WHERE approved_story_v2data IS DISTINCT FROM public_v2_data) AS differs_current_public_v2_data,
 count(distinct submission_id) AS approved_submission_count,
 count(*) FILTER (WHERE EXISTS (
  SELECT 1 FROM public.story_moderation_action_logs actions
  WHERE actions.story_id::text=ap.story_id AND actions.created_at>ap.approved_at AND actions.created_at<=ap.created_at
    AND (actions.to_visibility IN ('private','unlisted')
         OR actions.to_state IN ('confirmed_rejected','ai_rejected','pending_ai','pending_human','moderation_unavailable'))
 )) AS post_approval_nonpublic_action,
 count(*) FILTER (WHERE EXISTS (
   SELECT 1 FROM public.story_content_translations tr
   WHERE tr.story_id=ap.story_id AND tr.created_at<=ap.created_at
 )) AS translation_cache_created_before_target,
 count(*) FILTER (WHERE EXISTS (
   SELECT 1 FROM public.story_content_translations tr
   WHERE tr.story_id=ap.story_id AND tr.updated_at<=ap.created_at
 )) AS current_translation_row_last_updated_before_target
FROM approved ap GROUP BY 1 ORDER BY 1;