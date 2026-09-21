# Power Apps Future Application Discovery Report

**Project:** MILSTRIP Intake Automation  
**Date:** 2026-09-21  
**Status:** Discovery complete; design may begin after the readiness gates in this report  
**Decision authority:** Ed Lopez (HOC)

## 1. Executive conclusion

The project is a good candidate for a Power Apps operator experience, but
Power Apps should not contain the MILSTRIP parsing rules or write directly to
the legacy logistics tables. The recommended future shape is:

```text
Power Apps canvas app
        |
        | custom connector over HTTPS
        v
MILSTRIP application API / worker
        |                 |
        |                 +--> controlled Rainbow delivery adapter
        v
Application-owned PostgreSQL schema
        |
        +--> restricted read-only reference adapter to legacy Azure SQL (optional)
```

The existing stable downstream pipeline remains outside this application:
`download_ship940` -> ADF -> `ShipMaster` -> Boomi -> SCALE. The new
application should own intake, validation, approval, submission state and
traceability only.

**Recommendation:** proceed to logical design and contract definition, but do
not start production implementation until the authoritative Rainbow contract,
database layout/connection details, Power Platform licensing, and the missing
source-package baseline are resolved.

## 2. Discovery basis

The repository establishes the following facts:

- Phase 1 is accepted and intentionally has zero database and network access.
- The deterministic domain contract is an exactly 80-character printable ASCII
  canonical record; input longer than 80 characters is rejected.
- The parser is conservative: ambiguous repairs are rejected and unique repairs
  remain `REQUIRES_REVIEW`.
- The current scope stops before Rainbow CSV/FTP delivery and before the new
  application database.
- Phase 3 is approved in principle as a separate application-owned database;
  its technology and schema are still open.
- No direct write to `staging_download_shipMILS` is planned. Rainbow is the
  proposed delivery boundary.
- The project has identified ten open questions. Q1, Q6, Q7 and Q8 block the
  Rainbow design; Q4 blocks the database design; Q9 blocks direct Freshservice
  intake.

The current workspace also has a concrete readiness issue: documentation and
tests refer to a `milstrip/` package, but that package is not present in the
workspace currently inspected. `pytest` is also unavailable in the active
Python environment. This report therefore treats the documented contracts and
test descriptions as discovery evidence, not as a verified runnable API.

## 3. Target user workflow

### Primary workflow

1. Operator opens the Power Apps canvas app.
2. Operator pastes the email or Freshservice text, or later selects a ticket.
3. App submits the text and source metadata to the application API.
4. API extracts candidate records, normalizes transport noise, parses fields,
   validates the record and stores the immutable intake result.
5. App displays each record with status, issues, changed positions and the
   canonical 80-character value.
6. Operator reviews `REQUIRES_REVIEW` records and records an explicit decision.
7. App shows a batch summary. Only eligible records can be prepared for export.
8. A separate confirmation action creates the Rainbow batch and records the
   delivery state. The first release should require confirmation before any
   upload.
9. App shows an audit-friendly history of the request, review, export and
   delivery outcome.

### Power Apps screens

| Screen | Responsibility |
| --- | --- |
| New intake | Paste text, source/ticket ID, customer/context metadata, submit |
| Processing result | Record list, status, field summary, validation issues |
| Record review | Canonical value, warnings, repair explanation, approve/reject |
| Batch review | Eligible rows, duplicate warnings, export summary, confirmation |
| Delivery history | Batch state, attempts, acknowledgement, failures |
| Administration | Restricted configuration and reference health, if needed |

The app should not expose raw secrets, database connection strings, FTP
credentials or unrestricted legacy data.

## 4. Recommended responsibility split

### Power Apps

- Authentication-aware operator interface.
- User input, review decisions and confirmation actions.
- Display of API results and controlled filtering/search.
- No fixed-width parsing logic duplicated in Power Fx.
- No direct writes to legacy tables until the original parser/handoff contract
  is recovered and approved. See `docs/MILSTRIP_LEGACY_FLOW_REVIEW.md`.

### Application API

- Reuse the existing parser/domain engine as the single source of truth.
- Expose stable DTOs rather than database tables to the app.
- Enforce authorization, validation, idempotency and state transitions.
- Store immutable input/result evidence according to retention policy.
- Coordinate export and delivery adapters.

### PostgreSQL

- Store application-owned workflow state and traceability.
- Store canonical records and structured validation issues.
- Store operator decisions and delivery attempts.
- Do not clone `dbo.staging_download_shipmils`, `dbo.staging_download_ship940`
  or `dbo.download_ship940`.
- Preserve the existing `dbo` flow; a future handoff adapter must target the
  recovered legacy boundary rather than inventing a parallel shipment store.

### Legacy Azure SQL

- The local PostgreSQL migration already contains the legacy `dbo` objects,
  including the raw MILSTRIP and 940 staging tables.
- The API must not write to those objects until the original SQL parser/SP or
  manual transformation contract is recovered and approved.
- Any future handoff must use a narrow adapter or approved procedure with
  idempotency, status verification and a dedicated least-privilege identity.

The evidence and corrective backend map are in
`docs/MILSTRIP_LEGACY_FLOW_REVIEW.md`.

### Rainbow

- Own the authoritative CSV and transfer contract.
- Receive only the approved payload at the agreed boundary.
- Define the delivery acknowledgement that closes the application workflow.

## 5. PostgreSQL assessment

PostgreSQL is not available yet. The design should therefore target a
replaceable PostgreSQL service with two deployment placeholders: a PostgreSQL
server hosted inside the TAB on-premises network, or PostgreSQL hosted on an
Azure virtual machine. The application API and Power Apps contract should be
identical in both cases.

The logical database arrangement is:

- dedicated schema, for example `milstrip_app`;
- separate roles for application read/write, migration and read-only support;
- separate DEV, TEST and PROD databases or isolated schemas as policy permits;
- TLS, private network path or approved gateway, connection timeouts and pooling;
- migrations owned by this application and no changes to unrelated schemas;
- database audit/logging without raw email payloads unless explicitly approved.

The hosting comparison and placeholder network diagrams are in
`docs/POSTGRESQL_HOSTING_DESIGN.md`.

### PostgreSQL advantages

- Reuses existing database operations, backups and monitoring.
- Good fit for transactional workflow state and JSON diagnostics.
- Keeps the application data separate from the legacy WMS model.
- Avoids forcing Power Apps to understand operational database structure.

### PostgreSQL risks and conditions

- Capacity, maintenance windows, backup/restore, ownership and monitoring must
  be confirmed for whichever hosting target is selected.
- Power Apps' direct PostgreSQL connector is not the recommended primary
  integration boundary for this project. Licensing, gateway/network topology,
  connector limitations and table exposure would become coupled to the UI.
- The API hosting environment must have reliable private connectivity to
  PostgreSQL and the legacy reference source.
- If the selected target cannot offer isolation, TLS, roles and operational
  ownership, it is not ready for production.

### Alternatives

| Option | Assessment |
| --- | --- |
| Power Apps direct to PostgreSQL | Fast prototype, but weak boundary for parsing, authorization, idempotency and delivery state. Not recommended for production. |
| Power Apps + Dataverse | Strong Power Platform integration and governance, but adds licensing, platform dependency and a second data platform. Consider only if Dataverse is already standard and approved. |
| Power Apps + API + TAB-network PostgreSQL | Viable when the API can reach the TAB network through an approved private path or gateway. Best fit when on-premises data residency and existing operations are priorities. |
| Power Apps + API + PostgreSQL on Azure VM | Viable when Azure networking, VM hardening, patching, backup and administration are funded. Best fit when cloud-hosted API/database proximity and Azure operations are priorities. |

## 6. Proposed application data model

This is a logical model, not an approved physical schema. It must be reviewed
against DB1-DB6 before implementation.

| Entity | Purpose | Key data |
| --- | --- | --- |
| `intake_request` | One submitted source request | request ID, source type, source ID, submitted by, received time, payload retention reference, request hash |
| `milstrip_record` | One extracted candidate | record ID, request ID, sequence, raw candidate hash, normalized text, canonical text, DIC/family, status |
| `validation_issue` | Structured diagnostics | record ID, code, severity, field/position, message, repair metadata |
| `review_decision` | Human approval or rejection | record ID, decision, reason, actor, time, version |
| `export_batch` | A group prepared for Rainbow | batch ID, contract version, row count, content hash, state, created by |
| `export_batch_record` | Batch membership | batch ID, record ID, eligibility decision |
| `delivery_attempt` | Transfer evidence | batch ID, attempt number, endpoint environment, started/completed time, outcome, remote acknowledgement, error code |
| `audit_event` | State and security trace | aggregate ID, event type, actor/service, time, correlation ID, metadata |

Do not store full email/ticket content by default. Prefer a retention-approved
source reference plus the minimum payload needed to reproduce an operational
decision. If full payload retention is required, encrypt it, restrict access,
and set an explicit retention period.

## 7. API contract for design

The first API design should define versioned endpoints similar to these:

| Endpoint | Purpose |
| --- | --- |
| `POST /api/v1/intake/requests` | Submit text and source metadata; return request ID and processing result |
| `GET /api/v1/intake/requests/{id}` | Retrieve request, records, issues and current state |
| `POST /api/v1/records/{id}/review` | Record approve/reject decision with optimistic version |
| `POST /api/v1/batches/preview` | Validate selected records against export eligibility |
| `POST /api/v1/batches` | Create an immutable export batch after confirmation |
| `POST /api/v1/batches/{id}/deliver` | Start or request controlled delivery |
| `GET /api/v1/batches/{id}` | Return export and delivery evidence |
| `GET /api/v1/health` | Non-sensitive health and dependency status |

Every mutating operation should carry a correlation ID and idempotency key.
Responses should expose stable status codes such as `VALID`,
`REQUIRES_REVIEW`, `REJECTED`, `READY_FOR_EXPORT`, `DELIVERY_PENDING`,
`DELIVERED`, `DELIVERY_FAILED` and `OUTCOME_UNKNOWN`.

## 8. Security and operations design

### AD FS and SSO constraint

SSO is possible when the corporate domain is federated from Microsoft Entra ID
(formerly Azure AD) to the organization's AD FS service. In that arrangement:

- Power Apps authenticates users through the Entra tenant.
- Entra redirects federated users to AD FS for the corporate sign-in.
- The API and custom connector validate Entra-issued OAuth access tokens.
- Users can receive SSO through the existing AD FS/device/browser session,
  subject to the organization's AD FS claims, MFA and device policies.

Power Apps should not be designed to authenticate directly to an isolated AD FS
endpoint or to pass AD FS credentials to the API. If AD FS is not federated to
the Entra tenant that hosts Power Apps, the required prerequisite is to
configure that federation or use an approved Entra application-proxy/broker
pattern. The implementation design must confirm the verified domain, tenant,
AD FS federation metadata/claims, MFA policy, conditional access rules and
whether the API runs inside the corporate network or requires an approved
gateway/private connectivity path.

- Use Entra ID authentication for Power Apps and the API; authorize by
  role/group, not by hidden UI controls.
- Separate operator, reviewer, delivery-service, migration and support roles.
- Keep PostgreSQL and Rainbow secrets in an approved secret store. Never place
  them in Power Fx, environment variables committed to source, `.bat` files,
  API arguments or logs.
- Use managed identity where supported; otherwise use dedicated rotated
  credentials per environment.
- Use TLS and validate database certificates and SFTP/FTPS host keys as
  applicable.
- Log state transitions, actor, correlation ID, hashes and error codes. Avoid
  logging raw email, credentials, tokens and unnecessary DLA data.
- Add idempotency and duplicate detection before export. An unknown transfer
  outcome must not trigger blind resend.
- Define retention, backup, restore, incident response and support ownership
  before production enablement.
- Confirm Power Apps premium/custom-connector licensing and any gateway or
  network requirements before committing to the platform design.

## 9. Delivery phases

### Design phase: authorized now

1. Restore or attach the real `milstrip/` source package and test environment.
2. Freeze the API/domain DTO contract around the existing parser behavior.
3. Complete the Rainbow CSV and transfer questionnaire with authoritative
   samples and a non-production endpoint.
4. Complete DB1-DB6, including retention, environments, roles and PostgreSQL
   hosting constraints.
5. Produce the logical data model, threat model, Power Apps screen prototype,
   API OpenAPI contract and deployment topology.

### Implementation phase: gated

1. Extract the parser into a callable service without changing its rules.
2. Implement PostgreSQL migrations and repository tests in DEV only.
3. Implement API intake, review and state transitions.
4. Build the Power Apps canvas app against the custom connector.
5. Implement CSV serialization only from the approved Rainbow golden file.
6. Implement transfer only after protocol, acknowledgement, retry and
   duplicate rules are approved.
7. Run end-to-end tests with synthetic data, then a controlled non-production
   operational trial.
8. Require independent Full audit and explicit production GO.

### Explicitly defer

- direct writes to the legacy staging table;
- generic automatic repair of ambiguous records;
- copying the WMS schema into PostgreSQL;
- direct Power Apps access to production tables;
- automatic production upload without an initial human confirmation gate;
- Freshservice API ingestion until real export samples and access rules exist.

## 10. Readiness gates and owner decisions

The following are required before implementation can be authorized:

1. **Source baseline:** restore the `milstrip/` package, install dependencies and
   demonstrate the documented tests and type checks.
2. **Rainbow contract:** answer CSV1-CSV7 and FTP1-FTP8; provide a golden file
   and a safe test endpoint.
3. **Database contract:** answer DB1-DB6; confirm whether the existing
   PostgreSQL database can provide an isolated schema, roles, TLS, capacity and
   network path.
4. **Business rules:** define duplicate/resubmission behavior, supported DICs,
   A2 tail handling, A5E address handling and `REQUIRES_REVIEW` export policy.
5. **Power Platform:** confirm environment strategy, licensing for custom
   connectors, connector ownership, DLP policy and support model.
6. **Security/data governance:** confirm DLA data classification, retention,
   audit access and production identity ownership.

## 11. Proposed decision

Approve the next step as **logical design**, with the following architectural
direction:

> Power Apps canvas app + authenticated custom connector/API + application-owned
> PostgreSQL schema, with restricted read-only legacy references and Rainbow as
> the outbound boundary.

Do not approve production implementation, database changes, Rainbow transfer or
legacy integration yet. The project is ready to design the contracts and UX,
but it is not implementation-ready until the gates above are closed.

**Discovery status:** DONE_WITH_CONCERNS  
**Primary concerns:** missing runnable source package/test environment and
authoritative Rainbow/PostgreSQL contracts.  
**Next artifact:** approved logical data model, API contract and Power Apps
screen wireframe after owner answers the gated questions.

Power Apps migration readiness is tracked separately in
`docs/POWER_APPS_MIGRATION_READINESS.md`. The local PostgreSQL prerequisite is
now verified; UI migration and archive actions remain blocked because no old
UI or runnable parser package is present in this workspace.
