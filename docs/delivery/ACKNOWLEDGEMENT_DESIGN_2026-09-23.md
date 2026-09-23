# Intake and delivery acknowledgement

**Date:** September 23, 2026. **Status:** persistent intake receipt implemented
and verified in the saved, unpublished app. Production handoff and downstream
receipts are proposed work.

## Current receipt

The intake API returns HTTP 201 after its PostgreSQL transaction completes.
The response contains `request_id`, `received_at`, record count, rejected count
and review-required count. Source text, parsed records, issues and the intake
audit event are committed together. This confirms application persistence;
it does not confirm an order was sent.

The Results screen now keeps an **Intake saved** receipt separate from its
temporary message label. It shows the Request ID, received time and
**Validation at intake** counts. **Flagged for review** describes the original
validation result, not the number of outstanding reviewer decisions.
**Delivery: not connected** identifies the current delivery boundary.

The acknowledgement is displayed only when its Request ID matches the selected
request. For reopened requests, a matching request-detail response supplies the
received time. It supplies no aggregate counts, so the receipt omits counts
rather than treating a page of results as the whole batch. Refresh messages and
review decisions do not erase the receipt.

A saved request may contain rejected records or no candidates. Its receipt must
remain distinct from validation and human approval. There is no current legacy
writer, stored-procedure call, CSV export or Boomi receipt in this app.

Source evidence: [intake transaction and response](../../api/app.py),
[acknowledgement models](../../api/operator_models.py),
[Results controls](../../powerapps/canvas/scrResults.controls.yaml), and
[Intake recovery controls](../../powerapps/canvas/scrIntake.controls.yaml).

Live checks covered a mixed two-record intake, a zero-candidate intake,
refresh after submission and review, and reopening the first request while the
latest acknowledgement belonged to the second. Request/time matched database
readback; counts did not leak between requests. Both isolated test requests
were removed with exact-source and expected-state guards; absence was verified.
Studio confirmed all changes saved. See [guide verification](../operations-guide/VERIFICATION.md).

## Production confirmation

Use three separately evidenced milestones:

| Confirmation | Evidence required |
|---|---|
| Intake saved | Application transaction committed; Request ID returned. |
| Handoff completed | The selected production route accepted the same release command: committed business rows for SQL, or verified remote acceptance under the file-transfer contract. |
| Downstream received | The agreed receiving system returned a receipt correlated to that command, file or order. |

Display the receiving system, reference and time with its receipt. Do not label
this **Boomi received** unless Boomi actually supplies the agreed evidence.
Neither handoff nor receipt establishes shipment completion.

The recovered manual process is an external SQL batch that reads raw MILS
staging and writes directly to `download_ship940`. The similarly named staging
procedures serve a different path. The batch can set legacy `SENT` even when an
insert produces zero rows; that flag cannot drive application success.
See the [legacy review](../MILSTRIP_LEGACY_FLOW_REVIEW.md).

## Contracts still required

Select one release route: the recovered SQL handoff or the earlier Rainbow
CSV/FTP proposal. Define approved SQL writes, reference checks and transaction
boundaries, or the accepted CSV layout, transport and remote acceptance rule.
[ADR 0003](../adr/0003-rainbow-csv-ftp-is-the-delivery-boundary.md) records the
missing file and transfer contracts.

For either route, agree the receiving system, correlation key, receipt source,
polling or callback mechanism, timeout and escalation owner. Define duplicate
and partial-batch policy before enabling release. Upload completion alone is
not a consumer receipt.

## Ledger and recovery

Keep a durable release command with its ID, intake/record IDs, approved review
version, payload hash, route, attempts, timestamps and external references.
Record per-record outcomes separately from downstream acknowledgement. A
duplicate or rejected reference must not be counted as a new business write.

For the SQL route, commit business changes and their ledger evidence together.
For external transport, commit an outbox intent before sending and reconcile
remote results. Reusing a command ID must return its established result; reuse
with changed content must fail. Concurrent workers must not create two business
effects.

The present intake POST does not provide that idempotency contract: each call
creates a new Request ID. Its source ID supports reconciliation. After a
timeout, find the original request before submitting again. Review commands
already support retrying the same command; intake and review recovery differ.

For Azure SQL first and PostgreSQL later, preserve ledger IDs, hashes, review
versions, per-record outcomes and receipt references. Reconcile pending commands
at cutover and enforce one writer. A database change must not create a new
identity for an already accepted release.

## Acceptance cases

- Mixed and zero-record intakes show an accurate saved receipt; reopening another
  request never displays the previous request's time or counts.
- Refresh failure preserves the historical receipt while reporting unavailable
  results. Successful refresh and screenshot checks passed; an injected outage
  remains part of the outstanding canvas failure-path acceptance.
- A lost response after commit is **unknown**, not **failed**. Reconciliation
  discovers the original result before another business attempt.
- Concurrent retries create one effect. Duplicate orders retain the existing
  reference; validation/reference rejects retain their reasons.
- Partial batches show per-record outcomes and totals, never an unconditional
  batch success. The contract defines whether eligible rows proceed separately.
- Downstream rejection preserves the completed handoff and shows action
  required. Missing receipts show waiting/unknown with the last check time.
- Cutover preserves pending and completed commands, preventing lost work and
  duplicate releases across Azure SQL and PostgreSQL.
