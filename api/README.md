# Local MILSTRIP API

This is the first local API slice for the future Power Apps boundary. It owns
only application tables in the `milstrip_app` PostgreSQL schema. It must not
connect Power Apps directly to PostgreSQL or write to legacy operational tables.
The existing `dbo.staging_download_shipmils`, `dbo.staging_download_ship940`
and `dbo.download_ship940` tables remain the legacy flow; these new tables are
not copies of them.

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
```

The migration creates only `milstrip_app` and its tables, indexes and
constraints. It does not alter existing schemas or operational objects.

## Request example

```json
{
  "source_type": "PASTE",
  "source_id": "local-test-001",
  "source_text": "paste raw email or ticket text here",
  "submitted_by": "local-user"
}
```

The response is a persistence acknowledgement, not a validation result. Parser
results are included in the response, but no legacy table write is performed.

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
