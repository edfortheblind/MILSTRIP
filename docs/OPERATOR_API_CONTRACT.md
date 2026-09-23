# Local operator API contract

Version 0.2.0 — 2026-09-23. Extends the existing intake API without changing
its POST acknowledgement or request-detail GET fields. Scope: local development.

## Reads

All collection responses have `items` and nullable `next_cursor`. `limit` is
1-100, default 50. Treat cursors as opaque; they are validated and bound to the
endpoint, parent request and status filter. Invalid limits, filters or cursors
return 422. Pagination is keyset-based, not a frozen snapshot: refresh the first
page to see new requests or status changes.

| Route | Contents and order |
| --- | --- |
| `GET /api/v1/intake/requests` | Request metadata, excluding raw text. Optional `status` filter. Descending `(received_at, request_id)` |
| `GET /api/v1/intake/requests/{id}/records` | Record ID/sequence, validation status, raw/normalized/canonical values, structured issues, `review_version`, latest review. Ascending record sequence |
| `GET /api/v1/intake/requests/{id}/audit-events` | Events belonging to this request or its records, including actor and event data. Descending `(occurred_at, event_id)` |

Missing parent requests return 404 even when the collection would be empty.
Existing requests with no results return `items: []` and `next_cursor: null`.
Canonical strings retain all trailing spaces. Timestamps use ISO 8601 with a
timezone. Validation and review remain separate values.

## Review command

`POST /api/v1/records/{record_id}/review-decisions`

```json
{
  "decision": "REJECTED",
  "reason": "Operator requested a corrected source record",
  "expected_version": 0,
  "command_id": "10000000-0000-4000-8000-000000000001"
}
```

Decision is `APPROVED` or `REJECTED`; reason must contain 1-1000 nonblank
characters. `expected_version` is a nonnegative integer from the record read.
`command_id` is a client-generated UUID retained across retries of the same
command. Additional properties, including a caller-supplied actor, are rejected.

The transaction locks the record, checks for an existing command, checks version
and validation status, appends a decision, increments `review_version`, and
appends a `REVIEW_DECIDED` audit event. A failure rolls back all three writes.
Competing commands with the same expected version yield one success and one
409; the loser must reload before submitting another command.

First success returns 201 and the decision, actor, timestamp, command ID and
resulting review version. An exact retry returns the same decision with 200,
even after later decisions. Reusing a command ID with different payload or
reviewer returns 409. Command IDs are unique per record. Stale versions return
409; a missing record returns 404. Malformed bodies return 422.

Only a `VALID` or `REQUIRES_REVIEW` record can receive `APPROVED`; approval of
`REJECTED`, `RECEIVED`, `PROCESSING` or `FAILED` returns 409. A review approval
does not change validation status, canonical text or delivery eligibility. It
does not resolve A5E address requirements or make a legacy write possible.

## Local identity boundary

Review writes are disabled unless `MILSTRIP_LOCAL_REVIEWER` is explicitly set
to a nonblank local test identity (at most 200 characters). Missing configuration
returns 503. The peer and configured PostgreSQL host must both be loopback;
other peers/hosts return 403. Actor comes from server configuration, never the
request body or a forwarded identity header. This is a development control, not
SSO. Run Uvicorn on 127.0.0.1 with proxy-header trust disabled for these tests.

The existing intake and new reads remain local development endpoints. Do not
expose this service to shared users until authenticated identity/role handling
replaces the local review control. Database failures return 503 without SQL or
connection details. New routes bound database waits with transaction-local
lock and statement timeouts.

## Power Apps preparation

Intake screen: retain the request ID from the existing POST acknowledgement.
Results screen: page through records; show validation status and issues without
trimming canonical text. Review screen: display the current version, require a
reason, generate a command UUID once per action, and reuse it only for retries.
On 409 reload the record and ask the operator to reconcile. History screen:
page through scoped audit events. Never submit an actor from Power Fx.

The running app's `/openapi.json` is the schema source for connector preparation.
A matching reference artifact is in `docs/operator-api.openapi.json`. Regenerate
with `scripts/export_operator_openapi.py`; its `--check` mode detects drift.
This OpenAPI reference still needs the selected connector's format and identity
configuration before import/deployment.
The development Power Platform environment, reachable API and identity mapping
remain required before deploying a real connector or canvas app.

For laptop-first development, follow `docs/POWER_APPS_LAPTOP_DEV_SOP.md`.
The proposed standard-gateway route needs dedicated Basic authentication added
to this API and a connector-specific OpenAPI 2.0 definition. Neither is supplied
by the existing local-reviewer setting or by the runtime 3.1 schema export.
