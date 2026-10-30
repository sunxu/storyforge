-- R58 PRIORITY3: SERVER-SIDE HASH + HISTORY + EVENT CHAIN AUDIT.
-- SELECT-only, aggregate-only. Computes SHA256 in DB; never emits source text, story/user/message IDs or hashes.
-- These are PostgreSQL canonical UTF-8 text fingerprints, NOT historical API request-byte hashes.
-- The live cohort may drift; use in a single transaction/snapshot before controlled private capture.
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
 SELECT * FROM history WHERE created_at >= timestamptz '2026-10-26T07:05:10Z'
), proof AS MATERIALIZED (
 SELECT p.cohort,p.id,p.story_id,p.session_id,p.user_id,p.created_at,p.cp_gap,
   m.metadata AS target_metadata,m.content AS target_content,
   sub.snapshot->'source'->'v2Data' AS approved_story_card,
   sub.content_revision AS approval_revision,
   cp.snapshot AS checkpoint_snapshot,
   hist.hist_count,hist.history_json,hist.post_target_update_count,hist.hist_complete,
   hs.last12_count,hs.last12_completed,hs.first_user_offset,hs.first_role,hs.last_role,hs.roles_alternate,
   prev.metadata->'v2EventRuntimeAfter' AS prev_event_after,
   metric.logged_history_count
 FROM priority3 p JOIN public.v2_chat_messages m ON m.id=p.id
 LEFT JOIN LATERAL (
  SELECT sub.snapshot,sub.content_revision FROM public.story_moderation_action_logs a
  JOIN public.story_moderation_submissions sub ON sub.id=a.submission_id
  WHERE a.story_id::text=p.story_id AND a.created_at<p.created_at
   AND a.to_state IN ('ai_approved','human_approved') AND a.to_visibility='public'
  ORDER BY a.created_at DESC,a.id DESC LIMIT 1
 )sub ON true
 LEFT JOIN LATERAL (
  SELECT c.snapshot,c.turn_index FROM public.v2_session_checkpoints c
  WHERE c.story_id=p.story_id AND c.user_id=p.user_id AND c.session_id=p.session_id
   AND c.created_at<p.created_at AND c.turn_index*2<p.turn_index
  ORDER BY c.turn_index DESC,c.created_at DESC LIMIT 1
 )cp ON true
 LEFT JOIN LATERAL (
  SELECT count(*) AS hist_count,
   count(*) FILTER(WHERE h.status='completed') AS hist_complete,
   count(*) FILTER(WHERE EXISTS(
    SELECT 1 FROM public.v2_chat_message_ledger led
    WHERE led.session_id=p.session_id AND led.message_id=h.id
     AND led.user_id=p.user_id AND led.story_id=p.story_id AND led.recorded_at>p.created_at
   )) AS post_target_update_count,
   jsonb_agg(jsonb_build_object('turn',h.turn_index,'role',h.role,'status',h.status,'content',h.content)
       ORDER BY h.turn_index,h.id) AS history_json
  FROM (
   SELECT h.id,h.turn_index,h.role,h.status,h.content
   FROM public.v2_chat_messages h WHERE h.story_id=p.story_id AND h.user_id=p.user_id
    AND h.session_id=p.session_id AND h.turn_index<p.turn_index
   ORDER BY h.turn_index DESC,h.id DESC LIMIT 24
  )h
 )hist ON true
 LEFT JOIN LATERAL(
  WITH recent12 AS(
   SELECT h.turn_index,h.role,h.status FROM public.v2_chat_messages h
   WHERE h.story_id=p.story_id AND h.session_id=p.session_id AND h.user_id=p.user_id
    AND h.turn_index<p.turn_index ORDER BY h.turn_index DESC,h.id DESC LIMIT 12
  ), ord AS (
   SELECT role,status,row_number() OVER(ORDER BY turn_index ASC) AS rn,
    lag(role) OVER(ORDER BY turn_index ASC) AS previous_role
   FROM recent12
  )
  SELECT count(*) AS last12_count,count(*) FILTER(WHERE status='completed') AS last12_completed,
   min(rn) FILTER(WHERE role='user') AS first_user_offset,
   (array_agg(role ORDER BY rn))[1] AS first_role,
   (array_agg(role ORDER BY rn DESC))[1] AS last_role,
   bool_and(previous_role IS NULL OR previous_role<>role) AS roles_alternate
  FROM ord
 )hs ON true
 LEFT JOIN LATERAL(
  SELECT v.metadata FROM public.v2_chat_messages v
  WHERE v.story_id=p.story_id AND v.session_id=p.session_id AND v.user_id=p.user_id
   AND v.role='assistant' AND v.status='completed' AND v.turn_index<p.turn_index
  ORDER BY v.turn_index DESC LIMIT 1
 )prev ON true
 LEFT JOIN LATERAL(
  SELECT l.token_breakdown->>'historyMsgCount' AS logged_history_count
  FROM public.chat_latency_metrics l
  WHERE l.story_id=p.story_id AND l.session_id=p.session_id AND l.user_id=p.user_id
  AND l.scene='v2-chat' AND l.status=200
   AND l.created_at BETWEEN p.created_at-interval '30 seconds' AND p.created_at+interval '30 seconds'
  ORDER BY abs(extract(epoch FROM(l.created_at-p.created_at))),l.id LIMIT 1
 )metric ON true
)
SELECT cohort,count(*) AS cases,
count(*) FILTER(WHERE approved_story_card IS NOT NULL AND approval_revision IS NOT NULL) AS approved_card_with_revision,
count(*) FILTER(WHERE checkpoint_snapshot IS NOT NULL) AS checkpoint_present,
count(*) FILTER(WHERE hist_count=24 AND hist_complete=24) AS history24_completed,
count(*) FILTER(WHERE post_target_update_count=0) AS history24_no_later_ledger_change,
count(*) FILTER(WHERE
 length(encode(sha256(convert_to(approved_story_card::text,'UTF8')),'hex'))=64
 AND length(encode(sha256(convert_to(checkpoint_snapshot::text,'UTF8')),'hex'))=64
 AND length(encode(sha256(convert_to(history_json::text,'UTF8')),'hex'))=64
 AND length(encode(sha256(convert_to(target_content,'UTF8')),'hex'))=64
) AS four_hashes_computed,
count(*) FILTER(WHERE last12_count=12 AND last12_completed=12 AND first_role='assistant'
 AND first_user_offset=2 AND last_role='user' AND roles_alternate
 AND logged_history_count='11') AS recent12_align_to11_and_nearby_metric11,
count(*) FILTER(WHERE target_metadata->'v2EventRuntimeBefore' IS NOT NULL
 AND target_metadata->'v2EventRuntimeBefore'=prev_event_after) AS event_chain_jsonb_equal,
count(*) FILTER(WHERE target_metadata->'v2EventRuntimeBefore' IS NULL) AS event_chain_absent
FROM proof GROUP BY cohort ORDER BY cohort;