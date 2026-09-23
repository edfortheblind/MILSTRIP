# Operator API implementation evidence

Date: 2026-09-23. Status: implemented and verified for local development.

## Delivered

- Paginated intake metadata with status filtering and stable timestamp/ID order.
- Paginated record details with canonical spaces preserved, structured issues,
  latest review decision and version.
- Append-only review decisions, transactional audit and optimistic version
  checking; command UUIDs provide repeatable retries per record.
- Request-scoped, paginated audit history, including its record review events.
- Migration 005, contract documentation, OpenAPI reference artifact and a
  deterministic schema-export/check command.
- Power Apps intake/results/review/history behavior specified against this API.

The original intake POST acknowledgement and request-detail GET remain
compatible. Review is separate from validation; approval cannot rewrite a
record, clear a validation problem or enable a legacy submission.

## Verification

`MILSTRIP_TEST_DATABASE_URL` was set to the approved localhost development
database and `.venv/Scripts/python.exe -m pytest -q` passed **139 tests**.
The increment adds **33 HTTP/OpenAPI tests** to the prior 106-test baseline.

Tests cover pagination ties and new arrivals, bound/filter/cursor validation,
cross-request cursor rejection, empty/missing collections, canonical padding,
structured issues, exact retry, command reuse conflicts, stale versions,
review-required/rejected validation states, actor spoofing, local identity
controls, database failures, late audit failure and simulated commit failure.

Two independent PostgreSQL connections submitted conflicting review commands
concurrently. Exactly one returned **201**, the other **409**; the database
contained one decision, one version increment and one audit event. Synthetic
request, record, decision and audit rows were removed afterward. Most tests
use rollback-only transactions; this concurrency test commits synthetic metadata
and may advance application identity sequences. No legacy rows are written.

Migration 005 was installed on `localhost:5432/trav3pl-psqldb-stage`, limited to
`milstrip_app` columns and indexes. The installed parser still passed **18 cases
x 14 fields**. The generated OpenAPI artifact matches the runtime schema.

A temporary Uvicorn process bound to loopback with proxy-header trust disabled
passed real HTTP checks for database health, bounded request listing, OpenAPI
0.2.0, and a 404 for an unknown request's records. The process was stopped after
verification. No application server was left running.

Two dependency deprecation warnings were observed in Starlette's test client
(httpx and AnyIO compatibility paths); they did not fail the tests. Production
dependency qualification remains part of deployment preparation.

## Limits and next step

This is implementation self-verification, not an independent Audit. Existing
production governance remains applicable. No operational writer, SQL Server
cutover, shared deployment, connector or canvas app was created.

Review writes require explicit `MILSTRIP_LOCAL_REVIEWER` configuration and
loopback caller/database boundaries. This is local test identity, not Entra/AD
FS authentication. Intake/read routes retain their local-development boundary.
The next connected increment needs the Power Platform development environment,
an approved API access path, and identity/role mapping. Resolve the delivery
boundary before building an operational writer.
