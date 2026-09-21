# ADR 0002 — A new application database will be required

**Status:** Accepted in principle — 2026-08-14

**Decision owner:** Ed Lopez (HOC)

## Context

Phase 1 remains a local, zero-database parser. Phase 3 needs durable
application-owned state, traceability, validation results, idempotency and a
narrow connection to the legacy Travis 3PL platform. The owner has now decided
that this state must live in a new database rather than making the legacy
77-table operational database the new application's foundation.

## Decision

A future phase will create a separate database owned by the MILSTRIP
automation bounded context. It will not clone `ShipMaster`, inventory,
billing, carrier or other legacy domains.

The database technology, physical layout, table definitions and migration
sequence are deliberately not selected in this ADR. The owner will provide
the expected table layout; design will then evaluate Azure SQL versus other
practical options against the actual contracts. No connection or schema is
implemented in Phase 1.

The legacy database remains an integration dependency reached through the
smallest practical interfaces:

- restricted read access/views or procedures for ItemMaster, active DODAAC
  and duplicate checks;
- a narrow controlled submission procedure/contract for staging;
- separate identities and least privilege for read and write paths.

## Consequences

- Phase 3 database design cannot start until the supplied table layout and
  ownership/retention requirements are reviewed.
- Connection strings and credentials remain outside source control.
- Application state and shipment state must remain distinct.
- ADR 0001's deferral of the *technology/layout* remains valid, but its
  "whether a new database exists" question is resolved by this ADR.
