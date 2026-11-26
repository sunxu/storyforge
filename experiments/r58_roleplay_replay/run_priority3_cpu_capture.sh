#!/usr/bin/env bash
# R58 HF CPU-only private source capture entrypoint. Does not train or invoke an AI model.
set -euo pipefail
set +x
umask 077

die() { printf 'HOLD: %s\n' "$1" >&2; exit 42; }
for key in PGHOST PGPORT PGDATABASE PGUSER PGPASSWORD; do
  [[ -n "${!key:-}" ]] || die "required PostgreSQL env missing: $key"
done
[[ "$PGUSER" != postgres && "$PGUSER" != postgres.* ]] || die "use a dedicated read-only database role, not postgres"
export PGSSLMODE=require
export PGCONNECT_TIMEOUT=15
export PGOPTIONS="-c default_transaction_read_only=on -c statement_timeout=90000 -c lock_timeout=1000"

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
SQL="$SRC_DIR/PRIVATE_PRIORITY3_QUARANTINE_EXPORT_TEMPLATE.sql"
SCRIPT="$SRC_DIR/capture_priority3.py"
[[ -f "$SQL" && -f "$SCRIPT" ]] || die "required source files unavailable"

if ! command -v psql >/dev/null 2>&1; then
  [[ "$(id -u)" -eq 0 ]] || die "psql missing and installer requires root"
  command -v apt-get >/dev/null 2>&1 || die "apt-get unavailable; install postgresql-client in the image"
  apt-get update -qq >/dev/null
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends postgresql-client ca-certificates >/dev/null
fi

python -m unittest discover -s "$SRC_DIR" -p 'test_capture_priority3.py' -q
[[ "$(psql -X -qAt -v ON_ERROR_STOP=1 -c 'SHOW transaction_read_only;')" == "on" ]] || die "database connection must enforce read-only"

ROOT="${R58_PRIVATE_PARENT:-/workspace/storyforge-r58-private}"
NAME="${R58_CAPTURE_NAME:-priority3_source_20261030_first_capture}"
mkdir -p -m 700 -- "$ROOT"
chmod 700 -- "$ROOT" || die "private bucket does not support required chmod"
[[ ! -e "$ROOT/$NAME" && ! -L "$ROOT/$NAME" ]] || die "capture name exists, refusing overwrite"

# psql stdout contains private records. Never echo or tee it to logs.
# pipefail: a DB or capture failure fails the entire Job.
psql -X -qAt -v ON_ERROR_STOP=1 -f "$SQL" \
  | python "$SCRIPT" --private-parent "$ROOT" --name "$NAME"

[[ -f "$ROOT/$NAME/CAPTURE_COMPLETE" ]] || die "capture completion marker missing"
python - "$ROOT/$NAME" <<'PY'
import hashlib, json, pathlib, sys
p = pathlib.Path(sys.argv[1])
manifest = json.loads((p / 'manifest.private.json').read_text(encoding='utf-8'))
data = (p / 'source.private.jsonl').read_bytes()
if hashlib.sha256(data).hexdigest() != manifest.get('raw_jsonl_sha256'):
    raise SystemExit('HOLD: private source file hash mismatch')
if manifest.get('stage') != 'PRIVATE_SOURCE_CAPTURE_ONLY__NOT_TRAIN_ADMITTED':
    raise SystemExit('HOLD: capture stage invalid')
if manifest.get('source_count') != 3:
    raise SystemExit('HOLD: expected 3 source records')
print('R58_PRIVATE_SOURCE_CAPTURE_VERIFIED: 3 records, not train-admitted')
PY
