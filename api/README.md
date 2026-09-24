# MILSTRIP API 0.4.0

**Current: September 24, 2026.** The API serves the published Stage and Prod
canvas apps through the existing custom connector and gateway. Stage uses local
PostgreSQL. Prod's profile is disabled without an independent target. Standalone
player acceptance is blocked by the current account's licensing; IT owns
resolution and no trial was started.

Each Basic credential selects one fixed server-side profile. The shared
SQLAlchemy Core repository supports PostgreSQL/psycopg and SQL Server/pyodbc.
Live Azure SQL acceptance remains pending. Runtime checks the database's
`environment_identity` before application operations; operators cannot choose
the destination. The API owns six `milstrip_app` tables, including this marker.
It does not connect Power Apps directly to a database or write legacy tables.
The recovered MILSTRIP owner-run flow is `dbo.staging_download_shipmils`
directly to `dbo.download_ship940`. It does not use `staging_download_ship940`.
The application tables are metadata, not copies of those operational tables.

## Current scope

Implemented here:

- `GET /api/v1/health` returns the fixed environment, provider, safe label,
  configuration revision and readiness after application read/identity checks.
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

Use [the administrator SOP](../docs/RUNTIME_CONFIGURATION.md) for the complete
procedure. From PowerShell in the repository root:

1. Install `api/requirements.txt` in `.venv`; a SQL Server target also needs
   Microsoft ODBC Driver 17 or 18 on the API host.
2. Prepare distinct API verifiers using `Set-LocalApiCredential.ps1 -Environment
   stage` and `-Environment prod` when they do not already exist. Both are needed
   even while Prod is disabled. Enter credentials privately.
3. Open `scripts/Configure-Runtime.ps1`. Configure and test each intended target;
   leave unconfigured Prod disabled. Application schema provisioning is a
   separate explicit operation through `Initialize-ApplicationDatabase.ps1`.
4. Save the pending configuration, then start `scripts/Start-LocalApi.ps1`.
   No virtual-environment activation is required. Use the same `-ConfigFile`
   or `MILSTRIP_RUNTIME_CONFIG_FILE` selection throughout setup and startup.
5. Verify the authenticated health response for each connection. HTTP 200 can
   report a disabled environment; check `environment` and `ready` as well.

All API operations require Basic authentication; the authenticated username
supplies intake and review audit identity. `MILSTRIP_LOCAL_REVIEWER` is obsolete.
The API listener remains loopback-only for the existing gateway. The configured
database may be local or an approved remote target. Remote PostgreSQL requires
verified TLS; SQL Server requires encryption and certificate verification.
Connection strings stay in restricted `.cred/runtime.json`; never paste them
into chat, app formulas or Git. Saving changes requires an API restart to activate
them. Both apps share that process and its restart schedule.

The following migrations describe the earlier local PostgreSQL installation.
They include parser functions and are not a provider-neutral setup script:

```text
db/migrations/001_create_milstrip_app.sql
db/migrations/002_milstrip_legacy_parse.sql
db/migrations/003_canonical_text_length.sql
db/migrations/004_parser_stock_contract.sql
db/migrations/005_operator_review.sql
```

For that historical installation, migration 003 changed canonical storage to
`text` so trailing spaces count toward the 80-character constraint. Migration
004 preserves the full stock/part input and rejects invalid transport input.
Migration 005 adds review versions, retry command IDs and pagination/review
indexes. New application destinations use the explicit provisioning entry point
above. It does not run these PostgreSQL parser-function migrations, transfer
history, or alter operational objects. Existing incompatible schemas need a
separate migration.

## Request example

```json
{
  "source_type": "PASTE",
  "source_id": "local-test-001",
  "source_text": "paste raw email or ticket text here",
  "submitted_by": "local-user"
}
```

The API derives the actor from authentication; the client's `submitted_by` value
does not override it. The response includes aggregate validation status and record counts. Detailed
records/issues are available through the new `/records` collection; the existing
request-detail GET remains compatible. No legacy table write is performed.

The pure PostgreSQL parser function is installed by
`db/migrations/002_milstrip_legacy_parse.sql`. The Python/PostgreSQL contract
test is `scripts/run_milstrip_psql_contract_test.py`.

## Historical local database state

On 2026-09-21 the migration was applied successfully and verified with the
PostgreSQL client. The database contains these five application tables under
`milstrip_app`:

- `intake_request`
- `milstrip_record`
- `validation_issue`
- `review_decision`
- `audit_event`

No legacy operational tables were referenced or modified by the migration.
The current profile increment adds `environment_identity`, bringing the runtime
table count to six. See [ADR 0005](../docs/adr/0005-runtime-profiles.md).

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

For synthetic local review, configure the dedicated Basic credential privately
and use the loopback launcher above. Actor is the authenticated API username;
the client sends a decision, reason, command UUID and expected record version.
The old local-reviewer environment setting grants no access. This connection
identity is not shared-user SSO.

See `docs/OPERATOR_API_CONTRACT.md` for paging, status codes, retry semantics and
the Power Apps screen/connector preparation contract. Review approval does not
change validation status or enable delivery. The reference OpenAPI artifact is
`docs/operator-api.openapi.json`; check it with
`.venv/Scripts/python.exe scripts/export_operator_openapi.py --check`.
