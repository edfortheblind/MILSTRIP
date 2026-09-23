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
python -m uvicorn api.app:app --reload
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
```

Apply all four in numeric order. Migration 003 changes canonical storage to
`text` so trailing spaces count toward the 80-character constraint. Migration
004 preserves the full stock/part input and rejects invalid transport input.
Changes are limited to `milstrip_app`; no operational objects are altered.

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
records/issues are stored in the application schema; the current GET endpoint
returns request metadata only. No legacy table write is performed.

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
and run `.venv/Scripts/python.exe -m pytest -q`. Database tests use rollback-only
application transactions, including transactional identity-sequence restarts.
Without the variable, integration cases are explicitly skipped.

`scripts/run_milstrip_psql_contract_test.py` checks the installed function
read-only across 18 cases and all 14 exposed fields. It requires migration 004.
It checks positional parsing, not SQL Server end-to-end or semantic-validation
parity. See `docs/delivery/BACKEND_CORRECTION_2026-09-23.md` for current evidence
and the owner-gated temporary-table handoff test.
