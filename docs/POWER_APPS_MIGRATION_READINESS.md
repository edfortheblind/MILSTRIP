# Power Apps Migration Readiness

**Date:** 2026-09-21  
**Status:** BLOCKED_PENDING_SOURCE_AND_POWER_PLATFORM_ACCESS

## Completed prerequisites

- Local Windows development is the authorized operating mode.
- PostgreSQL 18.6 is available on `localhost:5432`.
- Database `trav3pl-psqldb-stage` is reachable with the owner-provided local
  role.
- The isolated `milstrip_app` schema is applied and contains five standalone
  tables.
- The API boundary and database migration are documented.
- No container, Linux environment or legacy database object was introduced.

## Blocking findings

### 1. No old UI is present in this workspace

The repository contains a CLI design, tests and documentation, but no web UI,
Power Apps package, desktop UI or other frontend implementation. The current
`run_milstrip.bat` launcher is an operator entry point, not a UI that can be
mechanically migrated.

Therefore a direct UI/UX migration cannot begin until the old UI is supplied as
one of:

- an existing `.msapp` export;
- a Power Apps environment/application URL with owner-approved access;
- screenshots plus a workflow inventory; or
- source code for the existing UI, if it exists outside this workspace.

### 2. The documented parser package is absent

The tests and design documents refer to `milstrip/`, but that package is not in
the current workspace. The Power Apps API cannot safely implement the actual
workflow until the parser source or an approved replacement package is
restored. Power Fx must not become a second, divergent implementation of the
MILSTRIP rules.

### 3. Archive/decommission scope is not specified

Archiving old versions is potentially destructive or affects operational
availability. No files, Power Apps versions, environments or deployed
applications will be deleted, disabled or renamed until the owner identifies
the exact archive targets and approves the retention period and rollback path.

## Target migration flow

```text
Old UI/export + workflow evidence
        |
        v
Power Apps canvas app
        |
        | Entra/AD FS SSO through approved custom connector
        v
Local API -> milstrip_app PostgreSQL schema
        |
        v
Parser/domain engine -> review -> future Rainbow boundary
```

The first Power Apps release should reproduce the operator workflow, not copy
database tables into the app. PostgreSQL remains behind the API, and the app
must not write to legacy operational tables.

The live SQL Server database remains authoritative while PostgreSQL is a future
deployment target. Power Apps work must preserve the current SQL/manual flow
until parity, parser handoff and cutover approval are complete.

## Required owner inputs

1. Location/export of the old UI and permission to inspect it.
2. Power Platform environment name and permission to create or inspect a
   development canvas app/custom connector.
3. Whether the old UI is the current CLI workflow or a separate application.
4. Archive targets: files, app versions, environments and/or deployments.
5. Retention period, archive location and rollback owner.
6. Approval to restore the missing `milstrip/` package from its authoritative
   source, or approval to rebuild it from the accepted specification and
   fixtures.

## Current decision

Database/API work may continue locally. Power Apps migration and old-version
decommissioning remain blocked pending the inputs above. This is a source and
authorization boundary, not a PostgreSQL limitation.
