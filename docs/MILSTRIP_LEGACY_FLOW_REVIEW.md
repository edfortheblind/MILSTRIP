# MILSTRIP Legacy Flow Review and Corrective Map

**Date:** 2026-09-21  
**Status:** Owner-run parser recovered; parity and safe handoff design remain  
**Scope:** Read-only review of local PostgreSQL `trav3pl-psqldb-stage` and the `psql-migration` project artifacts
This review was extended on 2026-09-21 with a read-only connection to the
current SQL Server source `trav3pl-sql-eastus.database.windows.net`, database
`trav3pl-sqldb-eastus-prod`.

The owner-run source was subsequently found in
`inbox/MILSTRIP helper NewMultiple_Protoype 1.sql`.

## 1. Executive finding

The MILSTRIP application should be a parser/review front end for the existing legacy flow, not a replacement for the legacy shipment tables.

The local migrated PostgreSQL database contains the legacy objects:

```text
dbo.staging_download_shipmils   raw 80-character MILSTRIP intake
        |
        | missing/undiscovered original manual parser or transformation
        v
dbo.staging_download_ship940    downstream shipment staging
        |
        | dbo.sp_download_ship940_020_from_staging()
        v
dbo.download_ship940            established downstream record store
```

The exact transformation is not `staging_download_shipmils` to
`staging_download_ship940`. The recovered owner-run script transforms raw MILS
directly into `download_ship940`; `staging_download_ship940` is not used by this
manual path.

The live SQL catalog was checked further and contains no trigger, dependency
entry, view or synonym attached to `staging_download_shipMILS`. The owner-run
transformation is an external/manual SQL batch, which explains why it is not a
database module.

## 2. Evidence collected

### Legacy PostgreSQL objects

Read-only inspection of `trav3pl-psqldb-stage` found:

| Object | Evidence | Meaning |
| --- | ---: | --- |
| `dbo.staging_download_shipmils` | 119 rows | Existing raw MILSTRIP intake table |
| `dbo.download_ship940` | 2,587,016 estimated rows | Active-looking established downstream store |
| `dbo.staging_download_ship940` | 0 rows at review time | Current downstream staging queue is empty |
| `dbo.sp_download_ship940_020_from_staging()` | Present | Inserts from `staging_download_ship940` into `download_ship940` |
| `dbo.sp_download_ship940_015_interfacecontrol()` | Present | Records interface-control counts for `staging_download_ship940` |

All 119 raw MILSTRIP rows currently have `milsstatus = 'SENT'`, with dates from 2025-10-13 through 2026-08-14. This confirms historical use, but the `SENT` value alone does not prove the exact downstream handoff succeeded.

### Legacy raw table contract

`dbo.staging_download_shipmils` contains:

- `mils char(80)`;
- `entrydatetime`;
- `milsstatus`;
- four delivery-address fields;
- delivery city/state/ZIP/country;
- `internalid` primary key.

This is materially different from the new `milstrip_app` tables. It is a legacy raw-intake table, not a copy of the new application workflow model.

### Downstream routine contract

`dbo.sp_download_ship940_020_from_staging()` inserts mapped columns from `dbo.staging_download_ship940` into `dbo.download_ship940`, skips rows whose `mroid` already exists, requires `erp_order`, and validates `datecreated`. It does not read `dbo.staging_download_shipmils`.

`dbo.sp_download_ship940_015_interfacecontrol()` counts rows in `dbo.staging_download_ship940` by `downloadfile`; it also does not read the raw MILS table.

### Recovered owner-run parser contract

The inbox script defines the actual current MILSTRIP path:

```text
1. INSERT formatted 80-character MILS rows into dbo.staging_download_shipMILS.
2. Loop over rows where milsStatus IS NULL.
3. SUBSTRING fixed positions into download_ship940 fields.
4. Resolve DODAAC through dbo.cfg_dodaac_active.
5. Require the NSN to exist in dbo.ItemMaster.
6. Reject duplicate ERP_ORDER values already in dbo.download_ship940.
7. INSERT directly into dbo.download_ship940.
8. UPDATE the raw staging row to milsStatus = 'SENT'.
```

The script also handles A5E ship-to address exceptions through manually edited
variables, maps `ItemMaster.UM1` to the downstream UI, assigns
`OrderSourceType = 2`, sets `Note3PL` to a date plus `_milstrip`, and assigns
`SUPPLYCENTERRIC = 'SMS'`.

This confirms the new MILSTRIP application is intended to replace the manual
parse/transform step, while preserving the existing legacy table contracts and
downstream behavior. It should not route through `staging_download_ship940`.

### Legacy behavior that requires explicit parity treatment

- The script marks `milsStatus = 'SENT'` after the insert attempt even when the
        insert selected zero rows because of an unknown NSN, missing DODAAC or
        duplicate ERP order. The app should preserve the legacy outcome for
        compatibility but add an honest application audit state such as
        `INSERTED`, `SKIPPED_DUPLICATE`, `REJECTED_UNKNOWN_NSN`, or
        `REJECTED_UNKNOWN_DODAAC`.
- An initial filter uses ERP order and DIC, but the final anti-join rejects an
        existing ERP order regardless of DIC. The corrected dry run applies
        this stronger final rule and SQL-style trailing-space equivalence.
- DODAAC selection depends on signal code position 51: values before `J` use
        the first six requisition characters; values at or after `J` use positions
        45-50.
- Quantity is cast from positions 25-29 as an integer; the future parser must
        preserve this compatibility rule and explicitly decide how DLM `M` quantities
        are handled.
- `A5E` address data is supplied out of band by editing variables in the
        script; the app must make this an explicit review field, not an implicit
        default.
- Price resolution falls back to `ItemMaster.LIST_PRICE` because the current
        script's `@milsPrice` variable is not populated by the active path.

The recovered script is evidence of current behavior, not an authorization to
execute unchanged SQL against PostgreSQL. It must be translated into a tested
adapter with transaction boundaries, idempotency, honest status reporting and
least-privilege access.

### Live SQL Server comparison

The current SQL Server database was checked read-only on 2026-09-21:

| Object | SQL Server current rows | PostgreSQL local rows |
| --- | ---: | ---: |
| `dbo.staging_download_shipMILS` | 123 | 119 |
| `dbo.staging_download_ship940` | 0 | 0 |
| `dbo.download_ship940` | 2,609,989 | 2,586,765 at the earlier PostgreSQL check |

SQL Server raw MILS rows all currently have `milsstatus = 'SENT'`, spanning
2025-10-13 through 2026-09-11. The SQL Server table shapes match the expected
legacy contracts: 12 columns for raw MILS, 79 for 940 staging, and 102 for the
final 940 table. SQL Server has the same named downstream procedures, and their
definitions reference `staging_download_ship940`, not `staging_download_shipMILS`.

This proves PostgreSQL is a future deployment target and migration artifact,
not the current system of record. SQL Server remains authoritative until
PostgreSQL reaches controlled parity and the owner approves a cutover. No
decommissioning or dual-write behavior is authorized by this review.

## 3. What the new `milstrip_app` schema is allowed to own

The existing five tables are not legacy copies. They should remain limited to new application concerns:

| New table | Correct role |
| --- | --- |
| `milstrip_app.intake_request` | Source submission, hash, actor and intake lifecycle |
| `milstrip_app.milstrip_record` | Parsed candidate and canonical result linked to an intake |
| `milstrip_app.validation_issue` | Structured parser/review diagnostics |
| `milstrip_app.review_decision` | Human approval/rejection evidence |
| `milstrip_app.audit_event` | Application state/audit trail |

They must not become a second `download_ship940`, a second `staging_download_shipmils`, or a shadow copy of legacy shipment data.

## 4. Corrective target architecture

```text
Power Apps / local API
        |
        | 1. submit raw text
        v
milstrip_app.intake_request
        |
        | 2. parse using recovered parser engine
        v
milstrip_app.milstrip_record + validation_issue
        |
        | 3. operator review and approval
        v
Approved legacy handoff adapter
        |
        | 4. controlled contract, idempotency and status update
        v
dbo.staging_download_shipmils OR dbo.staging_download_ship940
        |
        | 5. existing stored procedure / downstream process
        v
dbo.download_ship940 -> existing ADF/ShipMaster/Boomi/SCALE flow
```

The corrected target is now known: the application will preserve the raw input
boundary in `staging_download_shipMILS`, then perform the recovered transform
against the legacy `download_ship940` contract. `staging_download_ship940` is a
separate downstream staging path and is not the target of this MILSTRIP manual
flow.

## 5. Corrective implementation map

### Keep

- The local Windows API and PostgreSQL 18.6 development target.
- The isolated `milstrip_app` schema for new intake/review/audit state.
- The deterministic parser contract: exact 80-character canonical output, conservative repair and explicit review status.
- The existing migrated `dbo` legacy objects and downstream procedures.

### Change

- Rename the API/database responsibility from generic persistence to application intake and review metadata.
- Add a legacy-boundary discovery phase before implementing any legacy write.
- Reuse the recovered original parser semantics and field mapping rather than reconstructing a second mapping from the new tables.
- Design the handoff as an adapter with a transaction, idempotency key, preflight validation, post-write verification and auditable status.

### Do not do

- Do not copy legacy rows into `milstrip_app`.
- Do not alter or recreate `dbo.staging_download_shipmils`.
- Do not write to `dbo.staging_download_ship940` for this MILSTRIP path.
- Do not write to `dbo.download_ship940` until the translated adapter passes
        parity tests and an owner-approved non-production handoff.
- Do not mark a record `SENT` merely because an insert was attempted.
- Do not assume the migrated PostgreSQL routines include the original parser.

## 6. Evidence required to unblock the backend

1. One owner-approved copy of the recovered parser script, now located at
        `inbox/MILSTRIP helper NewMultiple_Protoype 1.sql`.
2. Source and destination table contract: `staging_download_shipMILS` to
        `download_ship940`.
3. One sanitized input row and resulting `download_ship940` row.
4. Rules for `milsstatus`, duplicate detection, retry and correction/resubmit.
5. Confirmation whether the app may write directly to the legacy staging table or must call a stored procedure.
6. Required database role and transaction/locking expectations.
7. A non-production end-to-end test proving the existing downstream routine receives the app-created record without changing unrelated flows.

## 7. Backend decision

The current API may continue to store new intake metadata in `milstrip_app`.
The owner-run contract is recovered. A legacy-write endpoint remains blocked
until handoff acceptance and the remaining transaction/review decisions are
approved.

**Corrective status (2026-09-23):** `BACKEND_OWNER_ACCEPTED_IMPLEMENTATION_PREPARED`
**Database safety status:** `NO_LEGACY_OBJECTS_MODIFIED`  
**Cutover status:** `SQL_AUTHORITATIVE_PSQL_FUTURE_TARGET`  
**Next action:** implement the local API contracts and read slice described in
`docs/delivery/IMPLEMENTATION_PLAN.md`. The owner accepted the backend and
authorized preparation. The owner-approved synthetic temporary-table test passed
all 38 mapped fields, duplicate checks, rollback and retry on 2026-09-23.

The original 47-test/single-sample check was insufficient to establish broad
parity. The corrected local suite has 106 passing tests, including 18 parser
cases across all 14 exposed SQL fields, transport failures and API transaction
rollback. Migration 004 is installed locally. This is positional/application
evidence, not complete SQL Server operational parity.

The next read-only handoff gate also passed. The translated sample resolved
through `cfg_dodaac_active` and `ItemMaster`, produced the expected
`download_ship940` values, and was correctly classified as a duplicate existing
legacy order (`SL470162240DCV`). The dry run performed no legacy write.

The corrected ERP-order-only duplicate check and installed parser parity were
rerun on 2026-09-23. Full evidence and remaining gates are recorded in
`docs/delivery/BACKEND_CORRECTION_2026-09-23.md`.
