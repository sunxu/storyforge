-- REVIEW ONLY: Owner approved FULL historical request-event SELECT for
-- the existing r58_export_reader audit role (2026-11-20).
-- Apply manually with Supabase SQL Editor under a database administrator.
--
-- Scope: public.v2_chat_request_events, all historical and future rows,
-- SELECT only, only r58_export_reader (plus ordinary role inheritance).
-- No data changes, no table-wide PUBLIC grant, no BYPASSRLS, no RLS disable,
-- no extra access to message bodies or other tables.
--
-- Preflight: the existing SELECT grant and RLS must remain configured.
-- This migration intentionally does not alter either.
BEGIN;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_catalog.pg_roles
    WHERE rolname = 'r58_export_reader' AND NOT rolbypassrls
  ) THEN
    RAISE EXCEPTION 'R60_P2_READER_ROLE_MISSING_OR_BYPASSRLS_HOLD';
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM pg_catalog.pg_class c
    JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public'
      AND c.relname = 'v2_chat_request_events'
      AND c.relkind IN ('r', 'p')
      AND c.relrowsecurity
  ) THEN
    RAISE EXCEPTION 'R60_P2_EVENT_RLS_NOT_ENABLED_HOLD';
  END IF;

  IF NOT has_table_privilege(
    'r58_export_reader', 'public.v2_chat_request_events', 'SELECT'
  ) THEN
    RAISE EXCEPTION 'R60_P2_EVENT_SELECT_GRANT_MISSING_HOLD';
  END IF;
END
$$;

CREATE POLICY r60_p2_gold48_all_request_events_reader_select
ON public.v2_chat_request_events
AS PERMISSIVE
FOR SELECT
TO r58_export_reader
USING (true);

COMMIT;

-- Owner verification: 1 policy with a true predicate, no PUBLIC policy added.
SELECT
  policyname,
  cmd,
  permissive,
  roles,
  qual
FROM pg_catalog.pg_policies
WHERE schemaname = 'public'
  AND tablename = 'v2_chat_request_events'
  AND policyname = 'r60_p2_gold48_all_request_events_reader_select';

-- Optional OWNER rollback (run separately AFTER evaluation):
-- DROP POLICY IF EXISTS r60_p2_gold48_all_request_events_reader_select
-- ON public.v2_chat_request_events;
