**Status — September 24, 2026:** Both apps are published; licensing is resolved. Stage passed published-player connection and saved-results checks. Prod opens but is disabled pending database selection. In-app administration awaits acceptance. Review approval does not deliver an order.

## Use the app

Use **MILSTRIP Stage** for testing and **MILSTRIP Prod** after activation. Select **Check connection**; confirm the environment and **Ready**. The gateway, API and database must run.

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

For environment problems, stop and contact support. After recovery or restart, reconcile requests and history; unsaved input and pending commands are lost on closing. Provide environment, Request ID, record number, time and error.
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

Manual production loads MILS staging, checks references/duplicates, and writes the order table.
</details>

<details markdown="1" class="diagram-detail">
<summary>Current architecture and acceptance limits</summary>

![Separate app connections select fixed database profiles.](diagrams/02-current-architecture.svg)

Each app's API credential selects a separate database profile. PostgreSQL has runtime evidence; Azure SQL acceptance is pending. Corporate SSO connections are configured; individual-user enforcement and administration screens await deployment acceptance.
</details>

## Administrator: database configuration

<details markdown="1" class="planning-detail">
<summary>Current procedure: change a database destination on the host</summary>

![Administrator configuration screen with the replacement connection string hidden.](screens/runtime-configuration.png)

Run **Configure-Runtime.ps1** on the API host. Select the environment and provider; enter IT's connection string and certificate settings. Saved strings remain hidden.

Select **Test connection** to check access, tables and environment identity without changing data. Provision new destinations separately with approval. After a successful test, enable the environment and select **Save pending configuration**.

Stop intake, restart the API, then verify both apps' environments, availability and saved results. Saving alone does not change the running API.

Reconcile migrated requests, reviews and history before switching; a connection string does not transfer them. Backend releases and restarts affect both apps.
</details>

<details markdown="1" class="planning-detail">
<summary>In-app administration — awaiting acceptance</summary>

The implemented **Configuration** screen provides **Load configuration**, **Save draft**, **Test draft** and **Apply draft**. Strings stay hidden. Disable the environment before changing its destination. Once activated, this screen replaces the host editor.

In **Users**, administrators manage corporate access; two protected Owners retain full access. Additions require confirmed access to both apps and supporting flows. Removal denies API access immediately; pending sharing remains incomplete.

These screens have not passed published-player acceptance. Continue using the host procedure. IT's setup SOP records SSO configuration and the remaining user checks.
</details>

## Phase 2: two production periods

Publication alone does not activate production integration.

| Period | Implementation | Acceptance |
|---|---|---|
| **1 — Azure SQL** | Qualify separate Stage/Prod targets, SQL adapter, hosted API, authorization and handoff | SQL freeze resolved; runtime, pilot and recovery tests |
| **2 — PostgreSQL** | Migrate data, audit history and pending commands; qualify downstream integration | Accepted migration and one writer switch; target December 31, 2026 |

<details markdown="1" class="planning-detail">
<summary>Production decisions</summary>

Resolve the SQL freeze before writes. Select SQL handoff or Rainbow CSV/FTP; agree hosting, authorization and a receiver receipt. Procedure completion, file creation and SENT are not receipts.
</details>

<details markdown="1" class="diagram-detail">
<summary>Azure SQL architecture</summary>

![Proposed Azure SQL production architecture.](diagrams/04-phase2-azure-sql.svg)
</details>

<details markdown="1" class="diagram-detail">
<summary>Proposed release and acknowledgement flow</summary>

![Proposed release and acknowledgement.](diagrams/05-phase2-functional.svg)

Release requires approval, live checks, authorization and a durable command ID. Reconcile uncertain outcomes against that ID before retrying.
</details>

<details markdown="1" class="diagram-detail">
<summary>PostgreSQL architecture</summary>

![Proposed PostgreSQL production architecture.](diagrams/06-phase2-postgresql.svg)

Databases on one VM share outages.
</details>

<details markdown="1" class="planning-detail">
<summary>Capacity and cutover</summary>

Test both platforms at twice expected peak. Rehearse migration; stop writers, reconcile data and pending commands, then switch. Preserve new PostgreSQL writes before returning to SQL.
</details>

<details markdown="1" class="diagram-detail">
<summary>Transition schedule</summary>

![Qualification, production cutover and stabilization schedule.](diagrams/07-phase2-transition.svg)

Qualify for two months; retain SQL for 30 stable days after PostgreSQL acceptance. A December 31 launch extends retention into January 2027.
</details>

## About this edition

Version **1.4.0**. September 24 player checks and administration implementation status. App/configuration captures show the currently published workflow and host editor; screens use synthetic data. Production databases were not re-inspected.
