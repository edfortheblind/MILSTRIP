# Local MILSTRIP API

This is the first local API slice for the future Power Apps boundary. It owns
only application tables in the `milstrip_app` PostgreSQL schema. It must not
connect Power Apps directly to PostgreSQL or write to legacy operational tables.
The recovered MILSTRIP owner-run flow is `dbo.staging_download_shipmils`
directly to `dbo.download_ship940`. It does not use `staging_download_ship940`.
The application tables are metadata, not copies of those operational tables.

## Current scope

Implemented here:

- `GET /api/v1/health` checks API and PostgreSQL availability.
- `POST /api/v1/intake/requests` parses and stores a source request, records,
  validation issues and application status.
- `GET /api/v1/intake/requests/{request_id}` reads the stored request.
- `GET /api/v1/intake/requests` lists metadata with filtering and pagination.
- `GET /api/v1/intake/requests/{request_id}/records` returns records, issues,
  review versions and latest decisions.
- `POST /api/v1/records/{record_id}/review-decisions` records a local decision
  and audit event atomically, with version and retry checks.
- `GET /api/v1/intake/requests/{request_id}/audit-events` returns scoped history.
- SHA-256 is stored for duplicate detection groundwork.

The Python parser is now wired into this local API. The API persists only
`milstrip_app` metadata and stops before any legacy write.

Before adding a legacy-write endpoint, use the recovered owner-run contract and
complete the parity gate. See `docs/MILSTRIP_LEGACY_FLOW_REVIEW.md`.

## Local Windows setup

From PowerShell in the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r api\requirements.txt
$env:MILSTRIP_DATABASE_URL = 'postgresql://<local-user>:<local-password>@localhost:<port>/trav3pl-psqldb-stage'
python -m uvicorn api.app:app --reload --host 127.0.0.1 --no-proxy-headers
```

The verified local development target is PostgreSQL 18.6 on `localhost:5432`,
database `trav3pl-psqldb-stage`. The connection probe succeeded with the
owner-provided local role. The password is intentionally not documented here;
use the workstation's approved PostgreSQL authentication mechanism.

Do not commit the connection string. The placeholder above is intentionally
not a working credential. Use the local PostgreSQL authentication mechanism
already approved for the TAB development workstation.

Apply the migration with a PostgreSQL client or approved database tool while
connected to the intended local database:

```text
db/migrations/001_create_milstrip_app.sql
db/migrations/002_milstrip_legacy_parse.sql
db/migrations/003_canonical_text_length.sql
db/migrations/004_parser_stock_contract.sql
db/migrations/005_operator_review.sql
```

Apply all five in numeric order. Migration 003 changes canonical storage to
`text` so trailing spaces count toward the 80-character constraint. Migration
004 preserves the full stock/part input and rejects invalid transport input.
Migration 005 adds review versions, retry command IDs and pagination/review
indexes. Changes are limited to `milstrip_app`; no operational objects are altered.

## Request example

```json
{
  "source_type": "PASTE",
  "source_id": "local-test-001",
  "source_text": "paste raw email or ticket text here",
  "submitted_by": "local-user"
}
```

The response includes aggregate validation status and record counts. Detailed
records/issues are available through the new `/records` collection; the existing
request-detail GET remains compatible. No legacy table write is performed.

The pure PostgreSQL parser function is installed by
`db/migrations/002_milstrip_legacy_parse.sql`. The Python/PostgreSQL contract
test is `scripts/run_milstrip_psql_contract_test.py`.

## Verified local database state

On 2026-09-21 the migration was applied successfully and verified with the
PostgreSQL client. The database contains these five application tables under
`milstrip_app`:

- `intake_request`
- `milstrip_record`
- `validation_issue`
- `review_decision`
- `audit_event`

No legacy operational tables were referenced or modified by the migration.

## Backend verification

Set `MILSTRIP_TEST_DATABASE_URL` to the approved localhost development connection
and run `.venv/Scripts/python.exe -m pytest -q`. Apply migration 005 first.
Most database tests use rollback-only application transactions, including
transactional identity-sequence restarts. The concurrency test uses two real
committing sessions with one synthetic record and removes its rows afterward;
application identity sequences may advance. No legacy tables are written.
Without the variable, integration cases are explicitly skipped.

`scripts/run_milstrip_psql_contract_test.py` checks the installed function
read-only across 18 cases and all 14 exposed fields. It requires migration 004.
It checks positional parsing, not SQL Server end-to-end or semantic-validation
parity. See `docs/delivery/BACKEND_CORRECTION_2026-09-23.md` for current evidence
and the owner-gated temporary-table handoff test.

## Local operator review

For synthetic local review only, set `MILSTRIP_LOCAL_REVIEWER` to a local test
identity before launching the service with the loopback command above. Review
writes are disabled without that configuration. Actor is supplied by the server;
the client sends a decision, reason, command UUID and expected record version.
Never expose this local mode through a proxy or shared endpoint as SSO.

See `docs/OPERATOR_API_CONTRACT.md` for paging, status codes, retry semantics and
the Power Apps screen/connector preparation contract. Review approval does not
change validation status or enable delivery. The reference OpenAPI artifact is
`docs/operator-api.openapi.json`; check it with
`.venv/Scripts/python.exe scripts/export_operator_openapi.py --check`.
