-- R60 / review-only: explicit Owner approval required before production execution.
-- This file is intentionally NOT a StoryForge migration and must NOT be auto-applied.
-- First phase grants metadata columns only; never exposes request_envelope or
-- conversation_context. Run only with authorized DB administrator account.
--
-- NOTE: chat_latency_metrics previously has a TABLE-LEVEL SELECT grant for
-- r58_export_reader. We REVOKE that explicit grant before granting scoped
-- columns. This can change existing consumers; review dependencies first!
-- If inherited grants exist, they must be audited separately.
--
-- This policy grants access to metadata rows across all owners. It is NOT
-- tenant-scoped; the Owner must approve that specific scope. R60 client
-- must restrict returned results to aggregate SAFE counts.
BEGIN;

DO $$
BEGIN
  IF current_user = 'r58_export_reader' THEN
    RAISE EXCEPTION 'ADMIN_ROLE_REQUIRED';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='r58_export_reader') THEN
    RAISE EXCEPTION 'READER_ROLE_NOT_FOUND';
  END IF;
  IF EXISTS (
    SELECT 1
    FROM (VALUES ('v2_chat_reply_jobs'),
                 ('chat_abnormal_snapshot'),
                 ('chat_latency_metrics')) AS v(name)
    LEFT JOIN pg_catalog.pg_class c
       ON c.oid = to_regclass('public.' || v.name)
    WHERE c.oid IS NULL OR NOT c.relrowsecurity
  ) THEN
    RAISE EXCEPTION 'EXPECTED_RLS_TABLE_MISSING';
  END IF;
END $$;

GRANT USAGE ON SCHEMA public TO r58_export_reader;

-- Preserve existing service_role and application privileges.
GRANT SELECT (
  id, user_id, story_id, session_id, client_msg_id,
  user_turn, assistant_turn, model_id, status, attempt_count,
  created_at, started_at, completed_at
) ON public.v2_chat_reply_jobs TO r58_export_reader;

GRANT SELECT (
  id, created_at, expires_at, user_id, session_id, story_id,
  turn_index, model, abnormal_type, finish_reason,
  request_id, relay_request_id
) ON public.chat_abnormal_snapshot TO r58_export_reader;

-- CAUTION: the existing r58_export_reader table-level grant is revoked,
-- replacing it with scoped column SELECT. Audit any consumers first.
REVOKE SELECT ON public.chat_latency_metrics FROM r58_export_reader;
GRANT SELECT (
  id, created_at, user_id, session_id, story_id,
  request_id, relay_request_id, relay_trace_id, model,
  mapped_model, status, finish_reason, error_category
) ON public.chat_latency_metrics TO r58_export_reader;

CREATE POLICY r60_gold192_evidence_metadata_select
  ON public.v2_chat_reply_jobs
  FOR SELECT TO r58_export_reader USING (true);
CREATE POLICY r60_gold192_evidence_metadata_select
  ON public.chat_abnormal_snapshot
  FOR SELECT TO r58_export_reader USING (true);
CREATE POLICY r60_gold192_evidence_metadata_select
  ON public.chat_latency_metrics
  FOR SELECT TO r58_export_reader USING (true);

COMMIT;

-- After deployment: run owner-local catalog preflight as r58_export_reader.
-- No DDL/DML or service_role access should be attempted from StoryForge.
