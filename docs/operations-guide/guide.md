**Status — September 24, 2026:** Stage and Prod are published. Player access is blocked for the current account; IT is handling licensing. Stage passed Studio runtime tests against local PostgreSQL. Prod awaits a database. Approval records a review; delivery is not connected.

## Use the app

Use **MILSTRIP Stage** for testing. After activation, use **MILSTRIP Prod** for authorized work. Select **Check connection** and confirm the environment and **Ready**. The gateway, API and database must run.

<div class="screen-step-group" markdown="1">

![Stage reports Ready with synthetic source text entered.](screens/01-intake.png)

<ol class="steps" start="1">
<li><h3>Enter the source</h3><p>Paste the original email or ticket text. Obtain missing values from the source owner.</p></li>
<li><h3>Submit the intake</h3><p>Select <strong>Submit intake</strong> once. Confirm the <strong>Intake saved</strong> receipt and <strong>Request ID</strong>. Keep the ID for follow-up. If confirmation is missing, follow the submission recovery procedure below.</p></li>
</ol>

</div>

<div class="screen-step-group" markdown="1">

![Saved intake receipt and validation results.](screens/02-results.png)

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
<li><h3>Verify the audit event</h3><p>Select <strong>History</strong>, then <strong>Load / refresh history</strong>. Find <strong>REVIEW_DECIDED</strong>; use <strong>More history</strong> when enabled. Results shows the decision. The audit identifies the environment's connection, not the individual reviewer.</p></li>
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

Reload after recovery. If the environment is wrong or unavailable, stop and contact support. After restarting, reconcile requests and history; unsaved input and pending commands exist only in memory. Provide the environment, Request ID, record number, time and error.
</details>

<details markdown="1" class="diagram-detail">
<summary>Operator flowchart</summary>

![Current operator procedure and recovery branches.](diagrams/03-current-user-sop.svg)
</details>

## Understand the workflow

Canonical records contain 80 characters. Production item and address lookups remain outside the app.

| Confirmation | Meaning | Availability |
|---|---|---|
| Intake saved | Source and validation records stored; Request ID assigned | Current |
| Handoff completed | Agreed production destination accepted the handoff | Required in Phase 2 |
| Downstream received | Receiving system supplied a receipt | Required in Phase 2 |

<details markdown="1" class="diagram-detail">
<summary>Current functional flow</summary>

![Intake workflow alongside the separate manual production process.](diagrams/01-current-functional.svg)

The separate manual process loads raw MILS staging, checks references and duplicates, and writes to the order table.
</details>

<details markdown="1" class="diagram-detail">
<summary>Current architecture and acceptance limits</summary>

![Separate app connections select fixed database profiles through the existing API.](diagrams/02-current-architecture.svg)

Each API credential selects one environment. Stage and Prod cannot share a database. PostgreSQL has runtime evidence; the SQL Server adapter still requires an Azure SQL acceptance test. Individual-user authorization remains pending.
</details>

## Administrator: database configuration

<details markdown="1" class="planning-detail">
<summary>Change a database destination</summary>

![Administrator configuration screen with the replacement connection string hidden.](screens/runtime-configuration.png)

Run **Configure-Runtime.ps1** on the API host. Select **stage** or **prod**, choose **postgresql** or **sqlserver**, and enter IT's connection string and certificate settings. Existing strings remain hidden.

Select **Test connection**. It checks access, application tables and environment identity without changing data. New destinations need separately approved schema provisioning. Enable the environment only after the test succeeds, then select **Save pending configuration**.

Stop intake during the change. Restart the API and verify each app's environment, availability and saved results. Saving configuration alone does not redirect a running API.

Changing a string does not transfer requests, reviews or audit history. Reconcile migrated data before switching. Both apps share the API implementation: backend changes and restarts affect both. Separate apps isolate canvas releases, not backend deployments.
</details>

## Phase 2: two production periods

Publication alone does not activate production integration.

| Period | Implementation | Acceptance |
|---|---|---|
| **1 — Azure SQL** | Configure separate Stage/Prod targets; qualify the implemented adapter, hosted API, authorization and handoff | SQL freeze resolved; runtime, pilot and recovery tests |
| **2 — PostgreSQL** | Migrate application data, audit history and pending commands; qualify downstream integration | Accepted migration and one writer switch; target December 31, 2026 |

<details markdown="1" class="planning-detail">
<summary>Production decisions</summary>

Resolve the SQL freeze before new writes. Choose the recovered SQL handoff or Rainbow CSV/FTP route. Agree hosting, authorization and the downstream receipt source; procedure completion, file creation and SENT do not establish receipt.
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

Separate databases on one VM share its outage risk.
</details>

<details markdown="1" class="planning-detail">
<summary>Capacity and cutover</summary>

Measure workload and test both platforms at twice expected peak. Rehearse migration, stop writers, reconcile application data and pending commands, then switch. Recovery must preserve new PostgreSQL writes before returning to SQL.
</details>

<details markdown="1" class="diagram-detail">
<summary>Transition schedule</summary>

![Qualification, production cutover and stabilization schedule.](diagrams/07-phase2-transition.svg)

Allow two months of qualification and 30 stable days after PostgreSQL acceptance before deciding on SQL retirement. A December 31 launch extends retention into January 2027.
</details>

## About this edition

Version **1.3.0**. September 24 runtime tests and app/configuration captures. Screens use synthetic data. Production databases were not re-inspected.
