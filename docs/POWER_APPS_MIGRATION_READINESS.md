# Power Apps Migration Readiness

**Date:** 2026-09-23
**Status:** LOCAL_BACKEND_ACCEPTED_POWER_PLATFORM_INPUTS_PENDING

The owner confirmed that the laptop is the backend development environment.
Follow `docs/POWER_APPS_LAPTOP_DEV_SOP.md`: a Power Platform Developer workspace
holds the app/solution, while a standard gateway on the same laptop will connect
to the loopback API and local PostgreSQL. No cloud backend host is needed now.
The SOP ends at an authenticated CLI/gateway handoff; connector Basic
authentication still needs implementation before enabling the connection.

Operator API update: all four local review/read interfaces are implemented,
migration 005 is installed, and 139 tests pass. Use
`docs/OPERATOR_API_CONTRACT.md` and the exported OpenAPI reference for screen and
connector preparation. Deployment still needs the environment and identity
inputs below; the configured local reviewer is not SSO.

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

An existing UI is required only if this is a migration of that UI. A new canvas
app can be designed from the accepted operator workflow. For migration, supply
one of:

- an existing `.msapp` export;
- a Power Apps environment/application URL with owner-approved access;
- screenshots plus a workflow inventory; or
- source code for the existing UI, if it exists outside this workspace.

### 2. Parser/backend prerequisite resolved

The `milstrip/` package is restored and integrated. The owner accepted the local
backend after 106 passing tests and the controlled temporary-table handoff.
The review API contracts and endpoints are implemented as recorded in
`docs/delivery/OPERATOR_API_IMPLEMENTATION_2026-09-23.md`. Power Fx must not become a second,
divergent implementation of the MILSTRIP rules.

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

1. Whether to build a new canvas app or migrate an existing UI; for migration,
   the location/export and permission to inspect it.
2. Power Platform environment name and permission to create or inspect a
   development canvas app/custom connector.
3. Whether the old UI is the current CLI workflow or a separate application.
4. Archive targets: files, app versions, environments and/or deployments.
5. Retention period, archive location and rollback owner.
6. Completed laptop DEV handoff from the SOP: authenticated maker/PAC account,
   same-machine gateway and API health. Dedicated API development credentials
   are implemented after handoff; shared-user identity remains a later gate.

## Current decision

Local API implementation and Power Apps contract preparation may proceed from
the owner-accepted backend. Connected deployment needs the environment and
identity inputs above. Old-version decommissioning remains separately gated.
