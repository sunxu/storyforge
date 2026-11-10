-- R60 review-only rollback. Requires authorized DB admin.
-- IMPORTANT: restoring previous broad table grants depends on recorded
-- BEFORE snapshot; this rollback does not infer or recreate them.
-- Stop if other consumers now depend on this R60 metadata access.
BEGIN;
DROP POLICY IF EXISTS r60_gold192_evidence_metadata_select ON public.v2_chat_reply_jobs;
DROP POLICY IF EXISTS r60_gold192_evidence_metadata_select ON public.chat_abnormal_snapshot;
DROP POLICY IF EXISTS r60_gold192_evidence_metadata_select ON public.chat_latency_metrics;

REVOKE SELECT (
  id, user_id, story_id, session_id, client_msg_id,
  user_turn, assistant_turn, model_id, status, attempt_count,
  created_at, started_at, completed_at
) ON public.v2_chat_reply_jobs FROM r58_export_reader;

REVOKE SELECT (
  id, created_at, expires_at, user_id, session_id, story_id,
  turn_index, model, abnormal_type, finish_reason,
  request_id, relay_request_id
) ON public.chat_abnormal_snapshot FROM r58_export_reader;

REVOKE SELECT (
  id, created_at, user_id, session_id, story_id,
  request_id, relay_request_id, relay_trace_id, model,
  mapped_model, status, finish_reason, error_category
) ON public.chat_latency_metrics FROM r58_export_reader;

COMMIT;
-- If the BEFORE snapshot confirmed a direct table-level SELECT grant on
-- chat_latency_metrics, a separate approved GRANT SELECT ON that table
-- restores it. Do not blindly restore: initial has_table_privilege=TRUE
-- could also result from inherited permissions.
