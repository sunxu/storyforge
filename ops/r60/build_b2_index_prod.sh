#!/usr/bin/env bash
# R60 B2 Ledger index: operator-only production deployment.
# Do not run from CI. This script never reads local secrets files.
set +x
set -Eeuo pipefail
umask 077

fail() { printf 'R60_B2_STATUS: HOLD\nREASON: %s\n' "$1" >&2; exit 1; }

# These are attestations of independent DBA/Supabase observability checks.
[[ "${R60_B2_OWNER_APPROVED:-}" == "YES" ]] || fail "OWNER_CHANGE_APPROVAL_MISSING"
[[ "${R60_B2_DISK_APPROVED:-}" == "YES" ]] || fail "DISK_AND_TEMP_SPACE_NOT_VERIFIED"
[[ "${R60_B2_WAL_APPROVED:-}" == "YES" ]] || fail "WAL_AND_REPLICA_RISK_NOT_VERIFIED"
[[ "${R60_B2_WINDOW_APPROVED:-}" == "YES" ]] || fail "CHANGE_WINDOW_NOT_APPROVED"
[[ -n "${PGHOST:-}" && -n "${PGDATABASE:-}" && -n "${PGUSER:-}" ]]   || fail "PG_CONNECTION_ENV_INCOMPLETE"

case "${PGUSER}" in
  supabase_read_only_user|r58_export_reader|service_role)
    fail "READ_ONLY_OR_SERVICE_ROLE_NOT_ALLOWED"
    ;;
esac

command -v psql >/dev/null 2>&1 || fail "PSQL_NOT_INSTALLED"

# Existing index includes invalid entries: never use IF NOT EXISTS here.
# All verification is catalog-only, with no user content or private IDs emitted.
guard="$(psql -X -qAt -v ON_ERROR_STOP=1 -c "
SELECT CASE WHEN
  current_database() = 'postgres'
  AND current_setting('transaction_read_only') = 'off'
  AND current_setting('row_security') = 'on'
  AND current_user = (
    SELECT pg_get_userbyid(relowner)
    FROM pg_class WHERE oid = 'public.v2_chat_message_ledger'::regclass
  )
  AND (SELECT relkind = 'r' AND relpersistence = 'p'
       FROM pg_class WHERE oid = 'public.v2_chat_message_ledger'::regclass)
  AND to_regclass('public.idx_v2_chat_message_ledger_r60_b2') IS NULL
  AND NOT EXISTS (
    SELECT 1 FROM pg_stat_progress_create_index
    WHERE relid = 'public.v2_chat_message_ledger'::regclass
  )
THEN 'PASS' ELSE 'HOLD' END;")" || fail "CATALOG_GUARD_QUERY_FAILED"
[[ "$guard" == "PASS" ]] || fail "CATALOG_SECURITY_OR_EXISTENCE_GUARD_FAILED"

printf 'R60_B2_PREFLIGHT: PASS\n'
printf 'R60_B2_ACTION: CREATE_INDEX_CONCURRENTLY\n'

# Each -c is a separate protocol request; CREATE INDEX CONCURRENTLY must
# NEVER run inside BEGIN/COMMIT or psql --single-transaction.
# The timeout changes are session-local settings for this psql connection.
psql -X -q -v ON_ERROR_STOP=1   -c "SET lock_timeout = '5000ms'"   -c "SET statement_timeout = '0'"   -c "CREATE INDEX CONCURRENTLY idx_v2_chat_message_ledger_r60_b2
      ON public.v2_chat_message_ledger USING btree
      (session_id, story_id, recorded_at, id)
      INCLUDE (turn_index, message_id, role, operation)"   || fail "INDEX_BUILD_FAILED_CHECK_FOR_INVALID_RESIDUAL_INDEX"

# The named index must be ready AND valid, not merely present.
receipt="$(psql -X -qAt -v ON_ERROR_STOP=1 -c "
SELECT CASE WHEN EXISTS (
  SELECT 1 FROM pg_index i
  JOIN pg_class c ON c.oid = i.indexrelid
  WHERE i.indrelid = 'public.v2_chat_message_ledger'::regclass
    AND c.relname = 'idx_v2_chat_message_ledger_r60_b2'
    AND i.indisvalid AND i.indisready AND i.indislive
    AND pg_get_indexdef(c.oid) ILIKE
      '%(session_id, story_id, recorded_at, id) INCLUDE (turn_index, message_id, role, operation)%'
) THEN 'PASS' ELSE 'HOLD' END;")"   || fail "POST_BUILD_CATALOG_CHECK_FAILED"
[[ "$receipt" == "PASS" ]] || fail "POST_BUILD_INVALID_OR_DEFINITION_MISMATCH"

printf 'R60_B2_STATUS: BUILD_COMPLETE_INDEX_VALID\n'
printf 'R60_B2_PRIVATE_VALUES_EMITTED: false\n'
printf 'R60_B2_EXISTING_INDEXES_UNCHANGED: true\n'
printf 'R60_B2_NOTE: Query-plan and runtime validation remain separate.\n'
