# Runtime profiles and app publication — September 24, 2026

**Status: DONE_WITH_CONCERNS.** The Stage runtime is implemented and locally
tested. Stage and Prod publication and solution membership were observed in the
tenant. Their separate connections are verified; Prod reports its disabled
profile. Standalone player acceptance is blocked by account licensing, which the
owner assigned to IT. No trial was started. Prod still has no approved database
target.

## Tenant and database state

| Item | Observed result | Evidence source |
|---|---|---|
| Stage app | Existing app reused as **MILSTRIP Stage**; ID `7f1b64d0-d51a-4ec8-84ad-2b18fe8c2f82` | Lead agent's tenant UI readback |
| Stage publication | Published September 24 at **1:01:57 PM America/Chicago** | Lead agent's tenant UI readback |
| Prod app | **MILSTRIP Prod**, ID `0aa02d8b-c7fa-42cc-87e8-6d287bd4c897`; published September 24 at **1:15:52 PM America/Chicago** | Lead agent's maker publication toast |
| Solution membership | Existing MILSTRIP solution: two apps plus MILSTRIP Local Dev API; all three read back at **1:16 PM America/Chicago** | Lead agent's tenant UI readback |
| Shared resources | Existing connector and MILSTRIP-DEV-LAPTOP gateway retained; separate Stage/Prod connections | Implementation and tenant work |
| Prod gateway health | At **18:20:52 UTC**, `environment=prod`, `database=DISABLED`, `ready=false`; schema validation succeeded | Existing connector GetHealth response |
| Prod Studio health | Actual `varEnvironment` record contained `environment=prod`, `database=DISABLED`, `ready=false` | Lead agent's Studio variable inspection |
| Standalone player | Current account prompted for a Power Apps plan; no trial accepted; licensing assigned to IT | Lead agent's actual Prod player readback and owner direction |
| Stage database | Existing local PostgreSQL `trav3pl-psqldb-stage`; marker `stage`, schema version `1` | Read-only database verification at 18:14:40 UTC |
| Prod database | No approved target; profile disabled | Runtime configuration work |
| Azure SQL | Native SQL Server adapter and application DDL implemented; no live acceptance run | Dialect compilation and repository tests |

Publication does not host the API or database. The laptop, gateway, API and
PostgreSQL must remain available. Both apps share the API implementation,
connector contract and restart schedule.

The verified Prod connection was created at
`2026-09-24T17:48:44.3188874Z`. It is a separate connection to the existing
connector, not a second connector. Stage's wrong-environment connection was
blocked in Studio Preview; Prod's correctly bound Preview remained unavailable
because its profile is disabled. These checks do not complete licensed player
acceptance. Both app checkers reported zero formula errors and two pre-existing
literal-predicate warnings for the empty galleries.

The existing connector's Basic authentication field labels were corrected to
**Username** and **Password** and saved. These are display labels; credential
values are not included in this evidence.

## Published app backups

Published exports are retained outside the repository under
`%LOCALAPPDATA%\MILSTRIP\backups\`:

| File | SHA-256 |
|---|---|
| `MILSTRIP-Stage-20260924-published.msapp` | `7921718a6e6fdb4a9bdecbbcfec127ad3c521d7906a684a260a8d3a73e3b42ae` |
| `MILSTRIP-Prod-20260924-published.msapp` | `c6a4f00212e203018ff7fd53ec85422daa104ff7d3cf868b2145debede1ccf4f` |

The lead agent inspected the exported source and verified fixed `AppEnvironment`
values of `stage` and `prod`, environment guards on all four screens, and distinct
`LocalConnectionReferences`. This verifies the exported app bindings and source;
it does not resolve the player licensing requirement.

## Implemented behavior

- Each dedicated API credential selects one fixed Stage or Prod profile.
  Operator input and forwarded headers cannot select a database. Each request
  verifies the destination's environment and schema marker before using it.
- The administrator screen accepts a PostgreSQL or SQL Server connection string,
  keeps stored strings hidden, and tests database access, required columns and
  environment identity without writing application data.
- Saving configuration creates a new private revision. The running API retains
  its startup snapshot until restart. Stage and Prod require separate database
  targets and credential bindings; disabled profiles cannot process requests.
- Provisioning is an explicit operation confined to `milstrip_app`: five data
  tables and one environment marker. It preserves compatible existing objects
  and rows; it does not create a database or write operational shipment tables.
- The repository preserves receipt-after-commit behavior, canonical trailing
  spaces, review versions, idempotent review commands, scoped audit reads and
  cursor pagination across the two SQL dialects.

Configuration changes do not migrate existing requests, reviews or audit
history. Database moves need a separate migration and reconciliation procedure.
Application approval still records a review; it does not execute the production
SQL handoff, send a CSV or establish a downstream receipt.

## Verification

The final complete suite passed **242 tests in 91.34 seconds** after the
environment-override correction below. Two dependency warnings remain. Earlier
focused execution by the storage agent produced **55 passing API/operator/storage tests**, including real
PostgreSQL transactions and the two-session review race. The race produced one
successful command and one version conflict. Late-write failure and simulated
commit failure returned controlled errors without leaving partial changes.

The API was restarted with the corrected guard while the final suite was
running. After the restart, a fresh
Stage Studio Preview reported **Ready**, loaded recent requests and read results
successfully. The illustrated results screenshot was refreshed after that read.
This is post-restart Studio evidence; standalone player acceptance remains
blocked by licensing.

PostgreSQL integration fixtures roll back their synthetic changes and restore
identity sequence state. The concurrency test removes only the request it
creates. Neither retained runtime example below is part of that cleanup.

| Retained request | Intakes | Records | Reviews | Audit events |
|---|---:|---:|---:|---:|
| `ff3f3cb5-04f5-4135-af74-f8db41962673` | 1 | 2 | 1 | 2 |
| `1d0c784d-c3bf-495c-928c-0b66687a58a4` | 1 | 2 | 2 | 3 |

Both rows were independently read back from PostgreSQL at **18:14:40 UTC on
September 24**. No changes were made during that check. The earlier retained
test remains intact.

Read-only result queries are available for the
[Stage publication request](../../db/queries/retained_stage_publication_2026-09-24.sql)
and the [earlier runtime request](../../db/queries/retained_runtime_2026-09-24.sql).

SQL Server checks cover generated DDL, UTC timestamps, Unicode, UUIDs, canonical
length including trailing spaces, nullable unique review indexes and explicit
review locks. These compilation checks do not establish connectivity,
permissions, transaction behavior or workload acceptance on Azure SQL.

## Review findings and corrections

1. **Configuration selection:** the API launcher previously ignored the
   configuration screen's alternate file selection. It now follows the same
   precedence: explicit `-ConfigFile`, then `MILSTRIP_RUNTIME_CONFIG_FILE`, then
   the repository default.
2. **Inherited PostgreSQL overrides:** libpq can inherit routing and session
   settings outside the saved connection string. The repository now rejects
   `PGHOSTADDR`, `PGSERVICE`, `PGSERVICEFILE`, `PGOPTIONS` and `PGPASSFILE` before
   connecting. Five focused, no-network regression cases passed after this
   correction. A missing port is explicitly set to 5432 rather than inherited
   from `PGPORT`.
3. **Readiness:** health probes all required columns of all six application
   tables without reading rows. A rollback-only missing-column regression
   confirms schema drift is reported as unavailable.

The profiles, authentication, runtime and launcher review was separate from
their implementation. The persistence author reviewed its own code and
implemented the PostgreSQL override correction; that portion is a self-review.
These bounded reviews do not replace the project's production Audit gate.

## Remaining acceptance

- IT must resolve the current account's Power Apps licensing, then standalone
  player acceptance must be completed. The owner chose not to start a trial.
- Keep Prod disabled until an independent target is approved, provisioned,
  configured and tested. Publishing the app does not activate that database.
- Run live Azure SQL acceptance before activating that provider, including
  intake, review replay/conflict, rollback, canonical padding and audit readback.
- Approve and test any database migration separately. Verify historical data
  and new writes before releasing operators onto a different target.
- Individual-user authorization and production handoff/downstream
  acknowledgements remain separate work.

References: [runtime administration](../RUNTIME_CONFIGURATION.md),
[ADR 0005](../adr/0005-runtime-profiles.md),
[full app administration SOP](../../sop/powerapps-setup.md),
[illustrated operator guide](../operations-guide/index.html).
