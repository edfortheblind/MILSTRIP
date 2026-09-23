**Current status — September 23, 2026:** unpublished development app. Intake, validation, review and history have passed synthetic checks. Production delivery is not connected; approval records a review only.

## Use the app

Open **MILSTRIP Intake Dev** in Power Apps Studio and select **Preview**. The owner must have development services running. Use approved test data.

<div class="screen-step-group" markdown="1">

![Intake screen with synthetic source text.](screens/01-intake.png)

<ol class="steps" start="1">
<li><h3>Enter the source</h3><p>Paste the original email or ticket text. Obtain missing values from the source owner.</p></li>
<li><h3>Submit the intake</h3><p>Select <strong>Submit intake</strong> once. Confirm the <strong>Intake saved</strong> receipt and <strong>Request ID</strong>. Keep the ID for follow-up. If confirmation is missing, follow the submission recovery procedure below.</p></li>
</ol>

</div>

<div class="screen-step-group" markdown="1">

![Saved intake receipt with one valid record and one rejected record.](screens/02-results.png)

<ol class="steps" start="3">
<li><h3>Inspect the results</h3><p>Select <strong>Load / refresh results</strong>, then <strong>Inspect / review</strong> for each record. Read its validation issues. Use <strong>Next results page</strong> when enabled. The canonical record is read-only.</p></li>
</ol>

</div>

<div class="screen-step-group" markdown="1">

![Review screen showing a saved approval at version 1.](screens/03-review.png)

<ol class="steps" start="4">
<li><h3>Record your decision</h3><p>Choose <strong>APPROVED</strong> or <strong>REJECTED</strong>, enter a reason of 1–1,000 characters, and select <strong>Save review</strong>. Validation-REJECTED records cannot be approved. Resolve warnings against business evidence; reject or escalate unresolved issues.</p></li>
<li><h3>Verify the saved review</h3><p>Check the saved message and updated version. Select <strong>Results</strong>, then <strong>Load / refresh results</strong> to confirm the decision.</p></li>
</ol>

</div>

<div class="screen-step-group" markdown="1">

![History screen showing recorded review events.](screens/04-history.png)

<ol class="steps" start="6">
<li><h3>Verify the audit event</h3><p>Select <strong>History</strong>, then <strong>Load / refresh history</strong>. Find <strong>REVIEW_DECIDED</strong> for the record; use <strong>More history</strong> when enabled. History contains event metadata; the decision appears in Results. The development audit identifies the shared connection, not the individual reviewer.</p></li>
</ol>

</div>

### Recovery procedures

<details markdown="1" class="recovery">
<summary>Submission has no confirmation</summary>

Keep the source text and **source ID** shown in the error. Select **Load recent requests** and, if needed, **More requests**. Match the source ID and open the request. If absent, have the owner verify it was not saved before selecting **Allow new submission**. Repeated intake submissions can create duplicates.
</details>

<details markdown="1" class="recovery">
<summary>Validation requires correction or review</summary>

For **REJECTED**, obtain corrected source and submit a new intake; retain both Request IDs. For **REQUIRES_REVIEW**, check the evidence before deciding. Do not edit, trim or reconstruct the canonical record.
</details>

<details markdown="1" class="recovery">
<summary>Review is unconfirmed or conflicts with another review</summary>

For an unknown outcome, select **Retry same command** without changing the retained decision or reason. For a conflict, select **Reload after conflict**, inspect the current review and retained reason, then decide whether another review is needed.
</details>

<details markdown="1" class="recovery">
<summary>Service is unavailable or the app restarted</summary>

After recovery, reload before relying on displayed rows. After restarting the app, reconcile requests and history: unsaved input and pending commands are held only in memory. Give support the Request ID, record number, time and error.
</details>

<details markdown="1" class="diagram-detail">
<summary>Operator flowchart</summary>

![Current operator procedure and recovery branches.](diagrams/03-current-user-sop.svg)
</details>

## Understand the workflow

Accepted canonical records contain 80 characters. Production item and address lookups remain outside the app.

| Confirmation | Meaning | Availability |
|---|---|---|
| Intake saved | Source and validation records stored; Request ID assigned | Current |
| Handoff completed | Agreed production destination accepted the handoff | Required in Phase 2 |
| Downstream received | Receiving system supplied a receipt | Required in Phase 2 |

<details markdown="1" class="diagram-detail">
<summary>Current functional flow</summary>

![Development workflow alongside the separate manual production process.](diagrams/01-current-functional.svg)

The manual process loads raw MILS staging, checks references and duplicates, and writes to the order table. App checks have not exercised this downstream process.
</details>

<details markdown="1" class="diagram-detail">
<summary>Current architecture and acceptance limits</summary>

![Existing connector and gateway, laptop API and local PostgreSQL.](diagrams/02-current-architecture.svg)

The existing solution, connector and gateway reach a laptop API and local PostgreSQL. Remaining acceptance covers canvas accessibility, conflicts, outages and pagination; shared-user authorization is pending. API retry/conflict checks have standalone evidence.
</details>

## Phase 2: two production periods

Proposed work assumes a published app.

| Period | Implementation | Acceptance |
|---|---|---|
| **1 — Azure SQL** | Hosted API, individual authorization, SQL Server adapter, live checks and controlled handoff | Pilot, duplicate prevention, recovery and operator tests |
| **2 — PostgreSQL** | Migrate application data, audit history and pending commands; qualify downstream integration | Accepted migration and one writer switch; target December 31, 2026 |

<details markdown="1" class="planning-detail">
<summary>Production decisions</summary>

Resolve the recorded SQL freeze before new writes. Choose one route: recovered SQL handoff or the earlier Rainbow CSV/FTP proposal. Confirm hosting, roles, capacity and recovery ownership. Agree the downstream receipt source; procedure completion, file creation and the legacy SENT flag do not establish receipt.
</details>

<details markdown="1" class="diagram-detail">
<summary>Azure SQL architecture</summary>

![Proposed Azure SQL production architecture.](diagrams/04-phase2-azure-sql.svg)
</details>

<details markdown="1" class="diagram-detail">
<summary>Proposed release and acknowledgement flow</summary>

![Proposed approval, controlled release and acknowledgement.](diagrams/05-phase2-functional.svg)

Release requires current approval, live checks, an authorized role and a durable command ID. Reconcile uncertain outcomes against that command before another attempt.
</details>

<details markdown="1" class="diagram-detail">
<summary>PostgreSQL architecture</summary>

![Proposed PostgreSQL production architecture.](diagrams/06-phase2-postgresql.svg)

Separate Stage and Production services on one VM do not provide high availability.
</details>

<details markdown="1" class="planning-detail">
<summary>Capacity and cutover</summary>

Measure users, batch size, latency, database load and backlog. Test both platforms at twice the expected peak; tune before increasing capacity.

Rehearse, stop writers, capture and reconcile data and pending commands, then switch once. Include application and audit objects. Recovery must preserve new PostgreSQL writes before returning to SQL.
</details>

<details markdown="1" class="diagram-detail">
<summary>Transition schedule</summary>

![Qualification, production cutover and stabilization schedule.](diagrams/07-phase2-transition.svg)

Allow two months of qualification before cutover and 30 stable days after PostgreSQL acceptance before deciding on SQL retirement. A December 31 launch extends retention into January 2027.
</details>

## About this edition

Version **1.2.0**. Four real development screens use synthetic data. Evidence: September 23 canvas checks, September 21 legacy review and September 3 migration records; production was not re-inspected. Select **View larger** to inspect an image. Printing includes expanded details.
