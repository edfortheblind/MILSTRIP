# Sharing recovery and bounded permission evidence

**Date:** September 25, 2026

**Status:** Design only; implementation, native evidence and independent Audit pending.

This is a separate design pass for the authorized local correction. It changes
neither tenant permissions nor private control state. It does not accept SSO
cutover, Canvas publication or a production connection. The current Full
corrective gate remains; its referenced orchestration-loop and definition-of-done
files are absent, as recorded in `docs/master.md`.

## Evidence and decision

The [retained trial](MAKERS_PERMISSION_PAGINATION_2026-09-24.md) acquired the
sharing lease, then stalled on the first Makers read. Native cancellation left
the durable execution RUNNING. Earlier grants must remain untouched.
`ControlStore.mutate` already locks, validates and atomically replaces state;
lease removal already requires a CLOSED execution with a result digest. Reuse
that mechanism for a **host-only, canceled-before-mutation recovery**. Do not
expire leases or manufacture a successful `SharingResult`.

The Makers permission action exposes `app`, `api-version` and `$top`, with no
continuation input. Its native pagination threshold does not impose a hard page
or time bound. Installed Microsoft Power Apps PowerShell 1.0.45 also aggregates
continuations in an unbounded `InvokeApi` loop; `Get-PowerAppRoleAssignment`
uses that loop, and its principal filter runs afterward. Neither is a bounded
collector. These are distinct limitations of the current connector and module,
not evidence of an OAuth failure. See the official [Makers action
contract](https://learn.microsoft.com/en-us/connectors/powerappsforappmakers/#get-app-role-assignments)
and [native pagination behavior](https://learn.microsoft.com/en-us/azure/logic-apps/logic-apps-exceed-default-page-size-with-pagination).

## Trusted recovery contract

The recovery service is callable only by a local maintenance entry point with
an active Admin/Owner identity and explicit recovery intent. Do not add a public
broker operation accepting a client-supplied `canceled=true` assertion. A JSON
capture is evidence storage, not proof of origin. Offline fixtures can exercise
validation but cannot authorize changes to the real control store.

The host collector obtains native run and action **metadata only**, through the
existing authenticated Microsoft tooling. It never follows inputsLink or
outputsLink, prints tokens, or exports protected action payloads. Require:

1. Exact tenant, environment, broker flow, native run, command, sharing plan,
   plan revision, execution and lease binding. The run has a terminal
   `Cancelled`/`Canceled` status and an end time; unknown status is rejected.
2. Complete action metadata against the inventory of the **executed flow
   version**, including nested branches. Lease acquisition succeeded and the
   recorded first read is consistent with the retained event. Every permission
   mutation was explicitly skipped, or has a fully evidenced skipped ancestor
   proving that its branch never ran. A missing action alone is not proof.
   No mutation may be Succeeded, Failed, Running, TimedOut or Canceled.
3. Every Management action and reservation step in that execution is proven
   not started. No active Management permit exists, and no open reservation
   belongs to the lease. Any uncertain call keeps the state locked.
4. Collection is complete and fresh (proposed maximum age: five minutes),
   timestamped after native cancellation. Duplicate action names, malformed
   times, continuation uncertainty, an uncorrelated executed definition or
   unexpected external actions reject recovery. Safe identifiers, statuses and
   timestamps are the evidence; success flags supplied by the caller are not
   substitutes.

### Run-attached definition evidence: September 25 clarification

The executed-inventory requirement does not require a field literally named
`workflow.version`. Microsoft documents GUID version identifiers and a changing
`workflowUniqueId`, rather than simple integer versions; see [drafts and
versioning](https://learn.microsoft.com/en-us/power-automate/drafts-versioning).
The historical run's ordinary response does not expose that field. Its exact
authenticated run GET with the fixed expansion `$expand=properties/flow`
provides a run-attached definition. Accept this as the inventory authority for
the one historical run pinned below when all of these conditions hold:

- The requested and returned run IDs match, and the attached flow resource
  ID/name agree within the expected environment. Both
  `properties.flow.properties.workflowEntityId` and
  `properties.flow.properties.definition.metadata.workflowEntityId` match the
  requested logical flow ID.
- The trusted collector hashes the complete attached definition using a
  documented serialization and projects its entire recursive action inventory,
  including types, connector operations, branch ancestry and safe literal broker
  operations needed to classify reservations. External action types and connector
  operations must be recognized. Started broker calls require reviewed static
  operations; a dynamic broker dispatch must be explicitly `Skipped`. No
  current-flow lookup substitutes for this response.
- Every inventory action has exactly one matching native action record, with no
  missing, duplicate or unexpected names for this historical run. Every
  permission mutation, Management action and reservation action is explicitly
  `Skipped`; the general skipped-ancestor allowance is unnecessary for this run.
- Run, attached definition and complete action metadata are collected together
  through the trusted authenticated collector and satisfy the same freshness
  limit. A stored projection, source label or hash alone cannot authorize apply.

The independent September 25 read-only assessment verified attached flow
`4e2df4b9-e7fd-e446-63fa-678b9612ca1f`, both logical-flow pointers
`04d6229f-5ab8-f111-aaac-7ced8d6f317c`, and definition SHA-256
`51891943a03f543679fc6c5faa9cabe4005081f26fcc82b98edeac2454a1113e`.
All 225 unique inventory names matched all 225 collected action names. All
16 permission mutations, 16 Management connector actions and 32 reservation/
permit-recording broker actions were `Skipped`; these categories overlap.
`Acquire_lease_add` succeeded and `Before_add_stage_app` was canceled. These
captures establish the accepted proof shape; their separate collection times
and age do not satisfy a future apply's fresh, single-collection requirement.

This is a bounded inference from the authenticated run relationship and exact
action correspondence. The Microsoft versioning documentation does not specify
this expansion's historical-snapshot semantics, and the returned attached GUID
is not proven to be `workflowUniqueId` or a version GUID. Describe the evidence
as a **run-attached definition**, retain its native flow identity and definition
digest, and leave absent native version fields null. `contentVersion=1.0.0.0`
is not service version proof. This clarification satisfies the historical
inventory gate; it does not establish the legacy run-to-execution mapping,
current absence of permits, authority, control revision or recovery eligibility.

**Legacy binding limitation:** the retained run's `AcquireSharingLease` stored a
UUID generated by `@guid()`, but not the native `workflow().run.name`. Status metadata
cannot independently reconstruct that association. For the retained run only,
pin the mapping documented in the September 24 report and record its provenance
as a historical operator-reviewed mapping. Do not generalize this exception to
arbitrary runs. If that mapping cannot be accepted as trustworthy during
independent review, preserve the lease until authoritative correlation is
available. Future lease acquisition should persist native run ID, native flow
ID and environment supplied by the trusted broker, with exact-match retry
validation, so recovery does not depend on historical notes.

The only historical mapping in scope is native Stage run
`08584113137259107903122568693CU13`, command
`689cf9a0-cfe5-4fc7-9496-bb1e2db0c32c`, plan
`b68690a1-837a-44ce-9950-248e4eb52df4`, execution
`fe7ea517-271b-4393-bfd0-f51657b9f99e`, and lease
`6ddd23d7-e3b6-458e-adfa-967bf5d91c81`. Qualification requires the retained
report, exact matching current control references, the live terminal run and
complete action metadata, and independent agreement that these jointly support
the historical association. The plan revision must come from current matching
control state, not an invented constant. The report alone never authorizes
closure; absent live metadata, stay pending.

Default the host command to preview. Emit a safe proposed-transition summary,
evidence digest and exact control revision. Applying requires those exact values
and a fresh revalidation; a changed revision/digest requires a new preview.

Inside one `ControlStore.mutate`, recheck current authority, exact plan/revision,
held lease/execution, operation ownership, all open Management reservations and
evidence digest. Reject stale/superseded plans for this narrow recovery; broader
recovery needs its own design. Close only the aborted execution, recording
`CLOSED`, a recovery digest, reason `NATIVE_CANCELED_BEFORE_MUTATION`, native run
identity and evidence timestamp. Remove only its matching lease. Leave the
command and plan pending, membership pending/denied, and observations/actual
grants unchanged. Append one safe audit event. Identical replay returns the
recorded result; changed evidence or binding is a conflict. A late broker
completion cannot replace this recorded recovery outcome. Write failure leaves
the prior durable state authoritative.

## Finite permission evidence

Implement a small deterministic host collector around a **single-page**
Microsoft authenticated request primitive, not the module's aggregate wrappers.
The installed `Invoke-Request` is an internal module function rather than a
normal exported command; validate its callable/module scope and HTTP behavior
before using it. No new tokens, copied bearer headers or service registration
are necessary for the design. Authentication must remain inside the existing
Microsoft session. This collector is read-only host diagnostics/recovery
infrastructure; app administrators continue using Power Apps for configuration.

Use fixed app IDs and the environment-scoped permissions route already used by
Microsoft's installed `Get-PowerAppRoleAssignment`. Construct the first URL
locally. Validate every continuation **before making its request**: HTTPS;
approved Microsoft endpoint; exact original app-permissions path; expected API
version/environment scope; no userinfo, fragment or unexpected query keys; no
redirects. Never expose a general URL proxy. Reject malformed, conflicting or
cross-resource continuation values. Treat the cursor as opaque within the
validated route. Both `nextLink` and `@odata.nextLink` must be accounted for.

Proposed bounds: 20 pages, fewer than 1,000 total rows, 30 seconds per request,
120 seconds overall, one request at a time and no automatic retries. Fail if
any bound is hit before a terminal page. A watchdog must enforce the deadline
even if the underlying synchronous request ignores timeouts. Repeated URLs,
repeated page content/assignment IDs, HTTP errors, malformed rows and redirects
fail closed. Empty pages carrying a valid continuation do not prove completion.
Validate the whole result before emitting a completed receipt; a found target
on page one never permits early success.

Only a terminal, structurally valid full traversal can prove presence or
absence. Match exact tenant/object ID and User type. Require one matching
CanView assignment; the already documented deployment Owner exception stays
specific to that object's ID. Unexpected roles or multiple assignments remain
unverified. Store only necessary permission identifiers and projection fields
privately; report bounded counts and fixed diagnostics publicly. Never activate
membership from app evidence alone: existing flow run-only evidence and the
entire current sharing plan still require verification.

**Native app gate remains:** host evidence collection does not repair the
interactive Makers action. The immediate generator improvement is to remove
the known-stalling native aggregation and keep single-page reads fail-closed
on any continuation or row-limit result. An explicit action timeout is useful
only after its support is verified; do not assert a hard bound on that connector
without evidence. No tenant sharing retry until a complete native read path is
accepted. If the existing connector cannot supply one, a separate connector or
host-backed adapter design must resolve authentication, DLP, deployment and
response protection before it is integrated. Do not grant first and hope later
readback works.

## Implementer task list and acceptance

1. Add strict recovery evidence validation and the host-only atomic transition;
   preserve existing callback and Management permit behavior. Add future native
   run binding without making historical records appear natively correlated.
2. Add a finite single-page collector and safe metadata projection. Keep live
   collection separate from fixture replay; refuse fixture evidence for real
   state changes. Record run/action/permission completeness independently.
3. Replace the generated Makers aggregation with its supported single-page
   fail-closed behavior and update generated artifacts and expectations. Record
   the unresolved native read gate rather than declaring sharing accepted.
4. Test valid cancellation, same-evidence replay, mismatched/old evidence,
   missing/skipped/started mutations, unknown run/version, conflicting lease,
   pending Management activity, stale plan, unauthorized caller, late callback,
   and persistence failure. Assert no membership activation or lost partial
   grants. Test missing/mismatched run-attached logical-flow pointers, inventory
   mismatch, unknown external calls, started dynamic broker dispatch and
   explicitly absent native version fields. Collector tests cover multi-page completion, target only on a later
   page, loops, URL escapes, redirects, time/page/row limits, malformed responses,
   ambiguous roles and secret-bearing error payload redaction.
5. Obtain independent review of the patch and the historical correlation before
   applying recovery. Native evidence can be collected read-only first. After
   trustworthy recovery, confirm the old execution is closed, its lease alone
   is released, the command/user remain pending, and no permit was cleared.
   Capture results separately from this design. Second-user acceptance, role
   enforcement and publication remain subsequent gates.

**DONE_WITH_CONCERNS:** design is complete; native correlation and the interactive
permission-read path remain explicit acceptance limits. No implementation or
private/tenant mutation was performed by this design pass.
