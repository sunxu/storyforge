-- R60 / P0B RolePlay generation evidence readiness: READ ONLY SQL.
-- Execute only through a trusted read-only connection, in the intended production DB.
-- No private message content, identifiers, object keys, secrets or grants are returned.
-- This is an operational snapshot; it cannot prove worker, gateway, TLS, or
-- provider live status. No migration, DDL, DML, SET ROLE, SECURITY DEFINER.
WITH names(tablename) AS (
  VALUES
    ('v2_generation_evidence'),
    ('v2_generation_evidence_exports'),
    ('v2_generation_evidence_grants'),
    ('v2_generation_evidence_request_links'),
    ('v2_generation_evidence_access'),
    ('v2_generation_evidence_grant_operations')
),
tables AS (
  SELECT n.tablename,
    c.oid IS NOT NULL AS exists_in_public,
    COALESCE(c.relrowsecurity, false) AS rls_enabled,
    CASE WHEN c.oid IS NULL THEN NULL ELSE has_table_privilege('anon', c.oid, 'SELECT') END AS anon_select,
    CASE WHEN c.oid IS NULL THEN NULL ELSE has_table_privilege('authenticated', c.oid, 'SELECT') END AS authenticated_select
  FROM names n
  LEFT JOIN pg_namespace ns ON ns.nspname='public'
  LEFT JOIN pg_class c ON c.relnamespace=ns.oid AND c.relname=n.tablename
    AND c.relkind IN ('r', 'p')
),
migration_names(name) AS (
  VALUES
    ('v2_generation_evidence_expand'),
    ('v2_generation_evidence_export_access'),
    ('v2_generation_evidence_grant_control'),
    ('v2_generation_evidence_request_links'),
    ('v2_generation_evidence_lifecycle')
),
migrations AS (
  SELECT m.name,
     count(sm.version) = 1 AS registered_exactly_once
  FROM migration_names m
  LEFT JOIN supabase_migrations.schema_migrations sm ON sm.name=m.name
  GROUP BY m.name
),
counts AS (
  SELECT jsonb_build_object(
    'v2_generation_evidence', (SELECT count(*) FROM public.v2_generation_evidence),
    'v2_generation_evidence_exports', (SELECT count(*) FROM public.v2_generation_evidence_exports),
    'v2_generation_evidence_grants', (SELECT count(*) FROM public.v2_generation_evidence_grants),
    'v2_generation_evidence_request_links', (SELECT count(*) FROM public.v2_generation_evidence_request_links),
    'v2_generation_evidence_access', (SELECT count(*) FROM public.v2_generation_evidence_access),
    'v2_generation_evidence_grant_operations', (SELECT count(*) FROM public.v2_generation_evidence_grant_operations)
  ) AS aggregate_counts
)
SELECT jsonb_build_object(
  'schema', 'storyforge_r60_p0b_roleplay_capture_readiness_snapshot_v1',
  'status', 'DB_STRUCTURE_ONLY__RUNTIME_AND_CAPTURE_AUTHORIZATION_HOLD',
  'tables', (SELECT jsonb_agg(to_jsonb(t) ORDER BY tablename) FROM tables t),
  'registered_migrations', (SELECT jsonb_agg(to_jsonb(m) ORDER BY name) FROM migrations m),
  'record_counts', counts.aggregate_counts,
  'production_worker_running_verified', false,
  'production_capture_enabled_verified', false,
  'provider_wire_provenance_verified', false,
  'training_authorized', false,
  'database_modified', false
) AS safe_snapshot
FROM counts;
