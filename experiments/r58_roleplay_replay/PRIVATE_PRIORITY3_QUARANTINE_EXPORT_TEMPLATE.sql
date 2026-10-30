-- DANGER: PRIVATE QUARANTINE EXPORT ONLY. THIS RETURNS FULL STORY CARD AND DIALOGUE TEXT!
-- NEVER execute through ChatGPT connectors, or commit/paste the results into GitHub/ChatGPT/SAFE reports.
-- Run only with the owner's scoped READ-ONLY database account inside HF private workspace, umask 077.
-- The statement is one SELECT, giving one PostgreSQL statement-level MVCC snapshot.
-- This does not assert original runtime request, independent worlds, model, locale or training admission.
-- R58 minimal 3-route replay priority, based on 10-case evidence-tier selection; read-only aggregation.
-- No identities or contents are returned. SQL uses 133 candidate LIVE cohort; does not freeze IDs.
-- 'metric_count_equals_raw_completed_count' is diagnostic only: real window is further pruned/scrubbed.
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
, scored AS MATERIALIZED (
 SELECT c.id,c.story_id,c.user_id,c.session_id,c.created_at,c.public_updated_at,c.author_id,
 m.turn_index,m.metadata,
 (SELECT (m.turn_index/2-cp.turn_index) FROM public.v2_session_checkpoints cp
  WHERE cp.story_id=c.story_id AND cp.session_id=c.session_id AND cp.user_id=c.user_id
   AND cp.created_at<=c.created_at AND cp.turn_index*2<m.turn_index
  ORDER BY cp.turn_index DESC,cp.created_at DESC LIMIT 1) AS cp_gap,
 (c.metadata ? 'v2EventRuntimeBefore') AS event_before,
 (SELECT count(*) FROM public.chat_latency_metrics l WHERE l.user_id=c.user_id AND l.story_id=c.story_id AND l.session_id=c.session_id
  AND l.scene='v2-chat' AND l.status=200 AND l.created_at BETWEEN c.created_at-interval '30 seconds' AND c.created_at+interval '30 seconds') AS metrics_30sec,
 CASE WHEN c.user_id=c.author_id THEN 'AUTHOR'
 WHEN c.public_updated_at>c.created_at THEN 'OLD_PUBLIC'
 ELSE 'CURRENT_PUBLIC' END AS cohort
 FROM candidates c JOIN public.v2_chat_messages m ON m.id=c.id
), eligible AS MATERIALIZED (
 SELECT *, CASE WHEN cp_gap<=5 AND metrics_30sec=1 AND event_before THEN 1
 WHEN cp_gap<=5 AND event_before THEN 2
 WHEN cp_gap<=5 THEN 3
 WHEN cp_gap<=20 THEN 4 ELSE 5 END AS evidence_rank
 FROM scored
), unique_per_story AS MATERIALIZED(
 SELECT *,row_number() OVER(PARTITION BY cohort,story_id ORDER BY evidence_rank,cp_gap,md5(id::text||':R58_PRIVATE_REPLAY_PILOT_20261030')) AS story_rn
 FROM eligible
), old_group AS MATERIALIZED(
 SELECT * FROM unique_per_story WHERE cohort='OLD_PUBLIC' AND story_rn=1 AND evidence_rank<=2
 ORDER BY evidence_rank,cp_gap,md5(story_id||':R58_PRIVATE_REPLAY_PILOT_20261030') LIMIT 3
), author_group AS MATERIALIZED(
 SELECT * FROM unique_per_story WHERE cohort='AUTHOR' AND story_rn=1 AND evidence_rank<=3
 AND story_id NOT IN (SELECT story_id FROM old_group)
 ORDER BY evidence_rank,cp_gap LIMIT 1
), current_group AS MATERIALIZED(
 SELECT * FROM unique_per_story WHERE cohort='CURRENT_PUBLIC' AND story_rn=1 AND evidence_rank=1
 AND story_id NOT IN (SELECT story_id FROM old_group)
 AND story_id NOT IN (SELECT story_id FROM author_group)
 ORDER BY evidence_rank,cp_gap,md5(story_id||':R58_PRIVATE_REPLAY_PILOT_20261030') LIMIT 6
), chosen AS MATERIALIZED(
 SELECT * FROM old_group UNION ALL SELECT * FROM author_group UNION ALL SELECT * FROM current_group
),
history AS MATERIALIZED (
 SELECT c.id,c.cohort,c.story_id,c.session_id,c.user_id,c.created_at,c.turn_index,c.cp_gap,
 x.hist_count,x.completed_count,x.failed_count,x.streaming_count,x.after_target_count,x.history_revised_count,
 x.messages_present_before,
 y.nearest_metric_history_count,y.nearest_metric_model
 FROM chosen c
 LEFT JOIN LATERAL (
  SELECT count(*) AS hist_count,
    count(*) FILTER(WHERE status='completed' AND role IN ('user','assistant')) AS completed_count,
    count(*) FILTER(WHERE status='failed') AS failed_count,
    count(*) FILTER(WHERE status='streaming') AS streaming_count,
    count(*) FILTER(WHERE created_at>c.created_at) AS after_target_count,
    count(*) FILTER(WHERE mutation_revision>0) AS history_revised_count,
    count(*) FILTER(WHERE created_at<=c.created_at) AS messages_present_before
  FROM (
    SELECT h.role,h.status,h.created_at,h.mutation_revision FROM public.v2_chat_messages h
    WHERE h.story_id=c.story_id AND h.session_id=c.session_id AND h.user_id=c.user_id AND h.turn_index<c.turn_index
    ORDER BY h.turn_index DESC LIMIT 24
  ) h24
 ) x ON TRUE
 LEFT JOIN LATERAL(
  SELECT (l.token_breakdown->>'historyMsgCount') AS nearest_metric_history_count,l.model AS nearest_metric_model
  FROM public.chat_latency_metrics l
  WHERE l.user_id=c.user_id AND l.story_id=c.story_id AND l.session_id=c.session_id
  AND l.scene='v2-chat' AND l.status=200 AND l.created_at BETWEEN c.created_at-interval '30 seconds' AND c.created_at+interval '30 seconds'
  ORDER BY abs(extract(epoch from(l.created_at-c.created_at))),l.id LIMIT 1
 ) y ON TRUE
)
, priority3 AS MATERIALIZED (
 SELECT * FROM history WHERE created_at>=timestamptz '2026-10-26T07:05:10Z'
), private_source AS MATERIALIZED (
 SELECT p.cohort,p.id AS target_message_id,p.story_id,p.session_id,p.user_id,p.turn_index,p.created_at,
 m.content AS target_text,m.metadata AS target_metadata,m.mutation_revision AS target_mutation_revision,
 moderation.id AS approved_submission_id,moderation.approval_at AS approved_at,moderation.content_revision AS approved_revision,
 moderation.snapshot->'source'->'v2Data' AS approved_story_card,
 ckpt.id AS checkpoint_id,ckpt.turn_index AS checkpoint_logical_turn,ckpt.created_at AS checkpoint_at,ckpt.snapshot AS checkpoint_snapshot,
 prev.history24,prev.n24,prev.n24_complete,prev.post_target_ledger_events,
 met.model AS nearby_metric_model,met.request_id AS nearby_metric_request_id,
 met.created_at AS nearby_metric_at,met.token_breakdown->>'historyMsgCount' AS nearby_metric_history_count
 FROM priority3 p
 JOIN public.v2_chat_messages m ON m.id=p.id
 LEFT JOIN LATERAL(
  SELECT sub.id,action.created_at AS approval_at,sub.content_revision,sub.snapshot
  FROM public.story_moderation_action_logs action
  JOIN public.story_moderation_submissions sub ON sub.id=action.submission_id
  WHERE action.story_id::text=p.story_id AND action.created_at<p.created_at
  AND action.to_state IN ('ai_approved','human_approved') AND action.to_visibility='public'
  ORDER BY action.created_at DESC,action.id DESC LIMIT 1
 ) moderation ON TRUE
 LEFT JOIN LATERAL (
  SELECT cp.id,cp.turn_index,cp.created_at,cp.snapshot FROM public.v2_session_checkpoints cp
  WHERE cp.story_id=p.story_id AND cp.session_id=p.session_id AND cp.user_id=p.user_id
   AND cp.created_at<p.created_at AND cp.turn_index*2<p.turn_index
  ORDER BY cp.turn_index DESC,cp.created_at DESC LIMIT 1
 )ckpt ON TRUE
 LEFT JOIN LATERAL (
  SELECT jsonb_agg(jsonb_build_object(
    'id',h.id,'turn_index',h.turn_index,'role',h.role,'status',h.status,
    'created_at',h.created_at,'content',h.content,'metadata',h.metadata,'mutation_revision',h.mutation_revision)
    ORDER BY h.turn_index,h.id) AS history24,
   count(*) AS n24,
   count(*) FILTER(WHERE h.status='completed') AS n24_complete,
   count(*) FILTER(WHERE EXISTS (
    SELECT 1 FROM public.v2_chat_message_ledger led
    WHERE led.session_id=p.session_id AND led.user_id=p.user_id AND led.story_id=p.story_id
      AND led.message_id=h.id AND led.recorded_at>p.created_at
   )) AS post_target_ledger_events
  FROM (
   SELECT h.id,h.turn_index,h.role,h.status,h.created_at,h.content,h.metadata,h.mutation_revision
   FROM public.v2_chat_messages h
   WHERE h.story_id=p.story_id AND h.session_id=p.session_id AND h.user_id=p.user_id
   AND h.turn_index<p.turn_index
   ORDER BY h.turn_index DESC,h.id DESC LIMIT 24
  )h
 )prev ON TRUE
 LEFT JOIN LATERAL(
  SELECT l.model,l.request_id,l.created_at,l.token_breakdown
  FROM public.chat_latency_metrics l
  WHERE l.story_id=p.story_id AND l.session_id=p.session_id AND l.user_id=p.user_id
   AND l.scene='v2-chat' AND l.status=200
   AND l.created_at BETWEEN p.created_at-interval '30 seconds' AND p.created_at+interval '30 seconds'
  ORDER BY abs(extract(epoch FROM(l.created_at-p.created_at))),l.id LIMIT 1
 )met ON TRUE
)
SELECT jsonb_build_object(
 'schema','storyforge-r58-priority3-private-quarantine-v1',
 'status','NOT_ADMITTED_NOT_BYTE_EXACT__REPLAY_PENDING',
 'source_commit_examined','e9fe29c42434caeb0bac5acc91845ab4741ecb2b',
 'deployed_source_commit_verified',false,
 'case',jsonb_build_object('cohort',cohort,'story_id',story_id,'session_id',session_id,
    'target_message_id',target_message_id,'turn_index',turn_index,'target_created_at',created_at),
 'historical_approved_story',jsonb_build_object('submission_id',approved_submission_id,
    'approval_at',approved_at,'content_revision',approved_revision,'v2_data',approved_story_card),
 'prior_checkpoint',jsonb_build_object('id',checkpoint_id,'turn_index',checkpoint_logical_turn,
    'created_at',checkpoint_at,'snapshot',checkpoint_snapshot),
 'history24',history24,
 'target',jsonb_build_object('content',target_text,'metadata',target_metadata,'mutation_revision',target_mutation_revision),
 'untrusted_nearby_metric',jsonb_build_object('model',nearby_metric_model,
    'request_id',nearby_metric_request_id,'recorded_at',nearby_metric_at,
    'history_msg_count',nearby_metric_history_count),
 'structural_checks',jsonb_build_object('prior_24_total',n24,'prior_24_completed',n24_complete,
    'post_target_ledger_events',post_target_ledger_events),
 'runtime_unknowns',jsonb_build_array('deploy_commit','locale','stale_translation','prompt_base_env',
    'dynamic_memory_RAG','retry_and_scrub','provider_request_bytes','request_id_exact_join')
 ) AS private_jsonl_row
FROM private_source
WHERE approved_story_card IS NOT NULL
 AND checkpoint_snapshot IS NOT NULL
 AND target_text IS NOT NULL AND btrim(target_text)<>''
 AND n24=24 AND n24_complete=24 AND post_target_ledger_events=0
ORDER BY CASE cohort WHEN 'AUTHOR' THEN 0 WHEN 'CURRENT_PUBLIC' THEN 1 ELSE 2 END, target_message_id;