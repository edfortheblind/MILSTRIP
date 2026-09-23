# MILSTRIP Intake Automation — Master Document

**Version:** 1.0 **Date:** 2026-09-23 **Status:** LOCAL_OPERATOR_API_IMPLEMENTED

Built with the AEKR (AI Engineering Knowledge Repo) workflow — see the root
`README.md` footer and `meta/OPERATING_PRINCIPLES.md` in the `AEKR` repo for
what that means. This document is this project's own single source of truth;
it does not duplicate that framework's content, only points at it.

## 0. Normative scope

This document binds the MILSTRIP intake automation project specifically. The
detailed field specification lives in `docs/MILSTRIP_SPEC.md` (normative for
the record format), architecture and the deferred integration decisions in
`docs/ARCHITECTURE.md` and `docs/adr/`, and the phased plan in
`docs/ROADMAP.md`. Durable decisions get an ADR under `docs/adr/`. Ed Lopez
(HOC) is the approval authority for scope changes, per the AEKR constitution
this project's `CLAUDE.md` / `AGENTS.md` carries.

## 1. What this is

Shawn Hinkle (Travis 3PL) manually repairs and formats urgent MILSTRIP orders
that arrive by email/Freshservice ticket before hand-typing them into a SQL
staging script. This project automates that specific, painful step — parsing
inconsistent human input into a correctly-formed 80-character MILSTRIP record
— without touching the stable pipeline downstream of it (`download_ship940`
→ ADF → `ShipMaster` → Boomi → SCALE). It is explicitly **not** a rebuild or
redesign of that downstream pipeline, the legacy 3PL database, or SCALE.

## 2. Governance profile

**Lean for normal Phase 1 operation; Full for the current corrective gate.**
Phase 1 was accepted after the August corrective audit. The September backend
corrections have implementation verification recorded in
`docs/delivery/BACKEND_CORRECTION_2026-09-23.md`; they have not received a new
independent Audit. The Full-profile orchestration-loop and definition-of-done
files referenced by the constitution are absent. Future database design and
any production-connected phase use Full/high-risk gates.

## 3. Confirmed scope of Phase 1 (accepted 2026-08-14)

**In:** extract raw pasted email/ticket text → conservative transport
normalization → family-aware structural + semantic validation → lossless
canonical 80-character MILSTRIP → human-readable/JSON report.
CLI + Windows `.bat` launcher. Zero database access. Zero network access.
Zero writes anywhere.

**Explicitly out (see `docs/ROADMAP.md` for when/if each returns):**
database validation (NSN/DODAAC lookups), submission to
`staging_download_shipMILS`, generic positional shift repair, Freshservice API intake, any web
or Power Apps UI.

## 4. Core domain model

See `docs/MILSTRIP_SPEC.md` and `docs/DISCOVERY_EVIDENCE.md`. Implemented in
`milstrip/domain.py::FIELD_SPECS` — that module and this spec must change
together.

## 5. System invariants

1. Nothing in Phase 1 ever writes to a database or the network.
2. A field value is never silently invented or auto-corrected without a
   deterministic rule backed by real evidence (see `MILSTRIP_SPEC.md` §
   Deterministic repair).
3. The canonical record is exactly 80 printable ASCII characters and preserves
   every received position; input over 80 is rejected, never truncated.
4. `milstrip/domain.py::FIELD_SPECS` is the positional source for parsing. The
   canonical builder preserves the validated normalized source line directly
   and only right-pads, preventing reconstruction from discarding data.
5. Application-facing deliverables, operator instructions, runtime messages
   and final interface contracts are written in English. Discovery evidence
   and internal research notes may remain in their source language.

## 6. Outstanding decisions and gates

- Phase 2 will create the final Rainbow CSV and deliver it through the vendor's
  FTP boundary. The CSV layout and connectivity contracts are pending; no
  serializer or network adapter is authorized yet. See ADR 0003.
- Application-owned persistence is implemented locally in PostgreSQL's
  `milstrip_app` schema under ADR 0004. Final hosting, identity and production
  connection design remain pending; ADR 0002 records the original requirement.
- Local development is now authorized against the owner's localhost PostgreSQL
  instance. The local migration may create only standalone objects inside the
  `milstrip_app` schema; it must not alter existing operational objects. See
  ADR 0004 and `docs/POSTGRESQL_HOSTING_DESIGN.md`.
- The local database review confirmed the migrated legacy MILSTRIP and 940
  tables already exist under `dbo`. The new `milstrip_app` tables are metadata
  for intake/review/audit, not copies of legacy business tables. The original
  raw-MILS SQL contract has been recovered. The approved temporary-table
  handoff test passed; independent review and operational acceptance remain
  pending. See
  `docs/MILSTRIP_LEGACY_FLOW_REVIEW.md`.
- The live SQL Server source remains authoritative while PostgreSQL is a future
  deployment target. PostgreSQL is not approved for cutover, dual-write or SQL
  decommissioning until controlled parity and the raw-MILS handoff contract are
  proven.
- The agreed migration route is documented in
  `docs/PSQL_INTELLIGENCE_ROADMAP.md`: develop PostgreSQL intelligence and new
  capabilities first, run a controlled two-month dry run with SQL still live,
  then migrate ownership and archive/decommission SQL only after approval.
- All ten items in `docs/OPEN_QUESTIONS.md` — none block Phase 1; several
  block specific later phases as noted there.
- Repository license/confidentiality classification (`OPEN_QUESTIONS.md` Q10)
  — a proprietary/internal default is in place pending Ed's confirmation.

## 7. Document control

Git history is the change log for this document. A durable, non-obvious
decision gets its own ADR under `docs/adr/` rather than a rewrite of this
file's prose. This document does not itself authorize any production
database change — see the governance profile note in § 2.

## 8. Phase 1 acceptance

Following the Full corrective audit, Ed Lopez approved P1-A, P2-A, P3-A and
P4-A on 2026-08-14. This accepts the local parser behavior and closes the
Phase 1 owner gate. It does not authorize Phase 2 CSV creation/delivery,
Rainbow production delivery, legacy table writes, or production database
changes. A local development database slice is separately authorized under
the `milstrip_app` isolation boundary. No legacy-table write is authorized
until the original parser/handoff contract is recovered and approved.

## 9. Current backend increment

The parser, local intake API, metadata migrations, pure PostgreSQL parser and
read-only legacy row mapper are present. The original one-case/six-field parity
check has been expanded to 18 cases and all 14 exposed SQL fields. Input stock
values retain all 15 positions; the 13-character legacy projection is blocked
when positions 21-22 are populated. Duplicate classification now uses ERP order
across all DICs. The test suite includes real PostgreSQL persistence and rollback
checks. Exact execution and deployment evidence is in the correction report.

The owner approved the synthetic temporary-table handoff test on 2026-09-23.
All 38 mapped columns, duplicate checks, rollback and retry passed; the temporary
target was removed. The owner subsequently accepted the backend ("all good
with the backend"), authorized commit/push and requested implementation
preparation. The next local increment is prepared in
`docs/delivery/IMPLEMENTATION_PLAN.md`: operator review API contracts, request
and record reads, then auditable review decisions and Power Apps preparation.
This owner acceptance is not an independent Audit result. Operational legacy
writes, shared frontend rollout and SQL Server retirement retain their separate
contracts and acceptance gates.

## 10. Operator API increment

The owner approved implementation of the prepared plan. Request listing,
record/issue detail, versioned/idempotent local review commands and scoped audit
history are implemented. Migration 005 is installed locally. The suite passes
139 tests, including real two-session review conflict verification; installed
parser parity and live loopback HTTP checks pass. See
`docs/delivery/OPERATOR_API_IMPLEMENTATION_2026-09-23.md` for evidence and
`docs/OPERATOR_API_CONTRACT.md` for the API and Power Apps preparation contract.

Local review identity is explicitly configured and is not shared-user
authentication. Power Platform environment access, an approved API path and
identity/role mapping are the next connected-integration inputs.

## 11. Laptop-first Power Apps development setup

The successful procedure is now [PowerApps setup](../sop/powerapps-setup.md).
See the [conversation record](../sop/conversation-record.md) for decisions and
the [restart prompt](../sop/restart-prompt.md) to continue in a separate session.

Current setup (2026-09-23): the owner used the existing organization Default
environment, created the MILSTRIP solution and MILSTRIP Local Dev API connector,
and registered the standard MILSTRIP-DEV-LAPTOP gateway. GetHealth returned
HTTP 200 through the gateway after correcting HTTPS to HTTP for loopback port
8000. The tested process exposes health only; Basic authentication enforcement
and application routes through the connector remain pending. The connector
export is in `powerapps/connectors/`; the supplied app icon is in `assets/`.
The pre-commit verification passed all 139 tests with the local database enabled
and confirmed the backend OpenAPI artifact matches the runtime schema.

The owner confirmed the laptop remains the development backend host. The
setup and handoff procedure is `docs/POWER_APPS_LAPTOP_DEV_SOP.md`: create/select
a Power Platform Developer workspace, register a standard gateway on the same
laptop and authenticate the local PAC CLI. This establishes prerequisites for
the agent to implement connector authentication and the development app.
The SOP describes the original setup recommendation; the existing Default
environment was used instead of creating a Developer environment. No cloud
API/database host is required at this stage. Power Apps
connector creation also needs an OpenAPI 2.0 artifact; the existing 3.1 export
remains the runtime API reference.
