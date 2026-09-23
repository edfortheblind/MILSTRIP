# Next implementation increment

Date: 2026-09-23. Status: local operator API implemented and verified.

Current continuation: dedicated local authentication and the expanded existing
connector are implemented; see `LOCAL_AUTH_CONNECTOR_2026-09-23.md` for evidence
and pending private credential, gateway and Studio acceptance steps.

The owner approved implementation. Completion evidence is in
`OPERATOR_API_IMPLEMENTATION_2026-09-23.md`; the contract is in
`docs/OPERATOR_API_CONTRACT.md`. All four interfaces below are implemented.

The owner accepted the backend and authorized commit/push and implementation
preparation. The verified baseline includes 106 passing tests, local migration
004, 18 parser parity cases across 14 fields, and a successful temporary-table
handoff checking 38 mapped columns, duplicates, rollback and retry.

## First slice: operator review API

Prepare the API contract that Power Apps will consume before building screens.
Extend the existing FastAPI service and `milstrip_app` schema. Keep parsing in
the existing Python package. No additional framework or hosting service is
needed for this local increment.

Implemented local interfaces:

| Interface | Behavior | Verification |
| --- | --- | --- |
| `GET /api/v1/intake/requests` | Bounded cursor pagination; optional validation-status filter; newest first with request-ID tie-breaker; omit raw source text | Stable pagination, empty pages, invalid filters, bounded limits |
| `GET /api/v1/intake/requests/{id}/records` | Ordered record results, canonical value, structured issues and latest review decision | Missing request, rejected records, preserved spaces, stable ordering |
| `POST /api/v1/records/{id}/review-decisions` | Append review decision and audit event atomically; require reason and expected record version | Missing record, stale version, conflicting concurrent decisions, rollback |
| `GET /api/v1/intake/requests/{id}/audit-events` | Paginated operator-visible history scoped to this request and its records | No unrelated events; deterministic ordering |

Keep validation status and review decision separate. Approval never changes
an invalid record into a valid one, silently repairs input, supplies an A5E
address, or grants delivery eligibility. Preserve original intake text and
candidate values. A correction must be linked to its original record and
revalidated; define that workflow before adding an editing endpoint.

## Completed implementation tasks

1. Specify request/response models, error codes and pagination rules in an API
   contract document and OpenAPI examples. Preserve the existing intake POST
   and request-detail GET response compatibility.
2. Implement request listing and record/issue detail reads first. Use database
   tests for filters, pagination, trailing spaces and missing records.
3. Define review concurrency/version and retry behavior; add an additive
   `milstrip_app` migration if necessary. Implement review plus audit as one
   transaction, with no caller-supplied identity trusted beyond local fixtures.
4. Add HTTP-level tests for serialization, validation errors and endpoint
   behavior, complementing the existing direct-handler database tests.
5. Prepare Power Apps screen/connector contracts: intake, results, review and
   history. Use synthetic fixtures until the development environment and
   identity configuration are supplied.
6. Run the full suite, installed-parser parity check, and relevant rollback
   checks. Update the evidence document and operator instructions.

Acceptance: operators can retrieve intake results and inspect issues; review
decisions remain auditable and cannot bypass validation; failure leaves no
partial decision/audit state; schema and API contracts match their consumers.

## Decisions needed for later integration

- Power Platform development environment/access and whether to adapt an
  existing app or create a new canvas app; an old UI is needed only for migration.
- Identity/role mapping and an authenticated development API path before any
  shared review endpoint or connector is exposed.
- Correction/resubmission rules, exception-address approval and who may
  resolve review-required records.
- Delivery boundary: ADR 0003 specifies Rainbow CSV/FTP, while the recovered
  SQL and temporary-table experiment establish a possible PostgreSQL legacy
  handoff. The experiment does not supersede ADR 0003. Resolve the intended
  delivery route in an ADR before implementing either operational writer.
- For a legacy writer: atomic duplicate handling, transaction scope, retry,
  staging/SENT outcomes, audit states and downstream acceptance. The sequential
  temporary-table guard is not a concurrent idempotency guarantee.

The local API slice and contract work are complete; the above decisions govern
the next connected increment.
Backend owner acceptance is recorded separately from independent Audit: no new
independent Audit has been performed. Production-connected work retains its
Full-profile acceptance requirements. SQL Server remains authoritative.
