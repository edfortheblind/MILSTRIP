# PostgreSQL Intelligence Platform Roadmap

**Continuation (2026-09-23):** the canvas draft is now implemented and tested with
synthetic data. The owner requested [two production operating periods](operations-guide/guide.md):
published app on existing Azure SQL first, then PostgreSQL after migration
acceptance, targeting end of Q4 2026. That plan preserves the two-month
qualification gate below and distinguishes it from the migration project's
30-day post-acceptance retention window. The sibling migration master's recorded
SQL freeze must be reconciled before P2.1 writes; publication and cutover are not
current facts.

**Date:** 2026-09-21  
**Decision:** PostgreSQL is the future intelligence and production platform. SQL
Server remains operational until the final migration gate.  
**Current state (2026-09-23):** SQL authoritative; PostgreSQL local backend
implemented and under correction/verification; recovered legacy SQL contract;
temporary-table handoff passed; independent review and operational acceptance pending.

## 1. Agreed operating model

```text
SQL Server current production flow
        |
        | remains live and protected during development/dry run
        v
PostgreSQL intelligence platform
        |
        +--> existing migrated business capabilities
        +--> new MILSTRIP parsing/review capability
        +--> future Power Apps operator experience
        +--> future incremental applications
```

The objective is not to copy SQL indefinitely or to build a parallel database
that ignores the existing flow. PostgreSQL must first reach controlled parity,
then add approved capabilities that SQL does not currently provide.

## 2. Route

### Step 0 - Protect the current production baseline

**Status:** Active

- Keep SQL Server as the current system of record.
- Do not decommission SQL Server, disable procedures, or change its tables.
- Do not introduce uncontrolled dual writes.
- Record a repeatable SQL baseline for the legacy flow: table counts,
  procedure results, MILSTRIP outcomes and operational timing.
- Treat PostgreSQL as the future target and development intelligence layer.

**Exit gate:** owner-approved SQL baseline and rollback position.

### Step 1 - Complete PostgreSQL local foundation

**Status:** In progress

- Keep PostgreSQL 18.6 on Windows as the local development target.
- Preserve the migrated `dbo` legacy objects and downstream procedures.
- Keep `milstrip_app` limited to new intake, parser result, review and audit
  metadata.
- Add migrations, tests, monitoring queries and a repeatable local reset/restore
  procedure without changing legacy behavior.

**Exit gate:** local PostgreSQL catalog, migrated legacy behavior and application
schema are validated; no legacy object is modified unexpectedly.

### Step 2 - Recover the current MILSTRIP manual contract

**Status:** Recovered; controlled handoff acceptance is pending

- Recovered the owner-run SQL batch in
  `inbox/MILSTRIP helper NewMultiple_Protoype 1.sql`.
- Confirmed it inserts raw MILS into `staging_download_shipMILS`, then inserts
  directly into `download_ship940`; it does not use `staging_download_ship940`.
- Capture one sanitized input/output lineage example and translate the batch.
- Document status, duplicate, retry, correction and `SENT` semantics.

**Exit gate:** approved source-to-destination contract and one reproducible
legacy test case.

### Step 3 - Implement the PostgreSQL MILSTRIP intelligence increment

**Status:** Implemented locally; corrected validation/parity under verification

- Restore or attach the accepted `milstrip/` parser package.
- Expose parsing through the local API; do not duplicate parsing in Power Fx.
- Persist only new application metadata in `milstrip_app`.
- Add review, approval, issue and audit states.
- Build a legacy handoff adapter only after Step 2 is approved.
- Make the adapter idempotent, transactional, least-privilege and verifiable.
- Keep a dry-run mode that parses and compares without writing legacy tables.

**Exit gate:** parser regression suite passes, parser output matches the accepted
contract, and a synthetic handoff passes without affecting unrelated data.

### Step 4 - PostgreSQL parity and intelligence qualification

**Status:** Planned

- Compare PostgreSQL migrated behavior against SQL Server using agreed golden
  cases and operational reports.
- Test the legacy MILSTRIP handoff against a controlled non-production path.
- Validate counts, statuses, duplicate handling, downstream procedure behavior,
  failures, retries and audit evidence.
- Add new PostgreSQL-only intelligence features only after the legacy parity
  baseline is stable.

**Exit gate:** independent review confirms no legacy capability was lost and
  every new capability has deterministic tests and operational ownership.

### Step 5 - Build Power Apps on the stable API contract

**Status:** After Steps 2-4

- Build the Power Apps canvas app for intake, review, approval and history.
- Use Entra ID federated with TAB AD FS for SSO.
- Call the API through an approved custom connector.
- Keep PostgreSQL and legacy tables behind the API.
- Reproduce the existing operator workflow before adding new UX features.

**Exit gate:** user acceptance with synthetic and approved non-production data;
no direct database access from Power Apps.

### Step 6 - Two-month controlled dry run

**Status:** Future cutover gate

SQL Server continues operating during the complete dry run. PostgreSQL runs the
new intelligence path in an explicitly approved mode:

- **Shadow mode:** parse and compare against SQL/manual results without
  affecting production downstream processing.
- **Controlled candidate mode:** PostgreSQL-generated output is reviewed and
  admitted through the approved handoff under owner-controlled test rules.
- **Production parallel mode:** only if explicitly authorized; avoid blind
  dual writes and define exactly which system owns each record.

Measure for the full two months:

- parser correctness and review rate;
- record counts and field-level parity;
- duplicate and retry behavior;
- downstream acceptance and failure outcomes;
- processing time and operator effort;
- PostgreSQL availability, backup/restore and audit completeness;
- unresolved incidents and rollback frequency.

**Exit gate:** two-month evidence pack, no unresolved critical/major defects,
owner sign-off and approved rollback plan.

### Step 7 - Final migration and SQL retirement

**Status:** Not authorized yet

- Freeze the accepted PostgreSQL release and database artifact.
- Back up and preserve SQL Server for rollback/reference.
- Switch the approved production ownership to PostgreSQL.
- Monitor the agreed stabilization period.
- Archive SQL Server according to retention and security policy.
- Decommission SQL Server only after explicit owner approval and confirmation
  that rollback is no longer required.

**Exit gate:** PostgreSQL is the declared system of record, downstream flows are
stable, the archive is verified, and decommission approval is recorded.

## 3. Immediate next actions

1. Review the correction evidence in `docs/delivery/BACKEND_CORRECTION_2026-09-23.md`.
2. Review the completed owner-approved temporary-table handoff evidence:
   all 38 mapped fields, duplicate checks, rollback and retry passed.
3. Obtain independent review of the backend contract and expand SQL Server
   parity evidence to operational outcomes, not just positional parsing.
4. Approve transaction, concurrency, retry, review and SENT/audit semantics
   before implementing a legacy writer.
5. Only after backend acceptance, design the Power Apps canvas app.

**Current gate:** `SQL_OPERATIONAL_PSQL_INTELLIGENCE_IN_DEVELOPMENT`  
**Final target:** `PSQL_PRODUCTION_SQL_ARCHIVED_AFTER_DRY_RUN`
