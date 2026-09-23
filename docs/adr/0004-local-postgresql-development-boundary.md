# ADR 0004: Local PostgreSQL Development Boundary

**Date:** 2026-09-21  
**Status:** Accepted for local development only  
**Owner:** Ed Lopez (HOC)

## Context

The future application needs persistence, but the production PostgreSQL hosting
target is not selected. The owner has a local PostgreSQL instance available for
development. That database also supports other work and must not be disturbed.

## Decision

The local MILSTRIP API may use the local PostgreSQL database through a
connection string supplied at runtime. The application may create and use only
the `milstrip_app` schema and objects owned by that schema.

The first migration creates standalone intake, record, issue, review and audit
tables. It does not alter, inspect, update or depend on existing operational
tables. No trigger or function is required for this increment.

Power Apps is not connected directly to PostgreSQL. The future Power Apps app
will call the API, and the API will own validation, authorization, transactions
and database connectivity.

## Consequences

- Local development can validate persistence before the final hosting decision.
- Existing database integrity is protected by schema isolation and a narrow
  migration review boundary.
- The local database is not a production environment and does not authorize
  production data, legacy writes or Rainbow delivery.
- The parser integration remains blocked until the documented `milstrip/`
  source package is restored to the workspace.

Update (2026-09-23): the parser package is restored and integrated. API
persistence/rollback verification is now covered by local database tests; see
`docs/delivery/BACKEND_CORRECTION_2026-09-23.md`. The original prerequisite above
is resolved; legacy writes and final deployment remain separately gated.
- Runtime connection strings and credentials stay outside the repository.

## Verification required before applying the migration

1. Confirm the target database and role using the approved local database tool.
2. Review the migration statements and verify every object uses `milstrip_app`.
3. Apply the migration once in the local development database.
4. Verify the five tables and indexes exist under `milstrip_app`.
5. Verify no objects outside `milstrip_app` changed.
6. Run API health and persistence checks with synthetic local data only.

## Local application

The migration was applied and verified on 2026-09-21 against the local
PostgreSQL 18.6 instance at `localhost:5432`, database
`trav3pl-psqldb-stage`. The verification returned exactly five tables under
`milstrip_app`. The later parser/API verification is recorded in the September
correction report; this original migration record is not production acceptance.
