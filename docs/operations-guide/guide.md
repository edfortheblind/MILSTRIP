# MILSTRIP, from intake to review

Paste the source. Check the records. Save a decision you can trace.

<div class="status-grid">
<div class="status-card current"><span class="eyebrow">Ready now · development</span><h2>Intake → review → history</h2><p>The four-screen app is saved and <strong>unpublished</strong>. Synthetic workflow checks passed.</p></div>
<div class="status-card limit"><span class="eyebrow">Not yet</span><h2>Production delivery</h2><p>There is no Send or Release action. <strong>APPROVED means reviewed, not sent or shipped.</strong></p></div>
<div class="status-card future"><span class="eyebrow">Next · proposed</span><h2>Azure SQL → PostgreSQL</h2><p>Phase 2 assumes a published app. PostgreSQL production is targeted for <strong>end of Q4 2026</strong>, after acceptance.</p></div>
</div>

**Evidence date: September 23, 2026.** This guide describes the recorded development app and proposed production plan. It is not a live service-status page. Sharing this file does not grant access to the app.

## Use the app

**For an authorized tester:** have the owner confirm the development laptop, API, database and gateway are running. Open **MILSTRIP Intake Dev** in Power Apps Studio, select **Preview**, and use approved test input.

<ol class="steps">
<li><h3>Paste the source</h3><p>On <strong>MILSTRIP intake</strong>, paste the original email or ticket text. Keep the source unchanged; obtain missing business values rather than guessing.</p></li>
<li><h3>Submit once</h3><p>Select <strong>Submit intake</strong> and wait for results. Keep the <strong>Request ID</strong>: it is your reference for this intake. If no result arrives, use the recovery steps below before submitting again.</p></li>
<li><h3>Check every record</h3><p>Select <strong>Load / refresh results</strong>, then <strong>Inspect / review</strong> beside a record. Read its status and issues; use <strong>Next results page</strong> when enabled. Accepted canonical output should be 80 characters; the field is read-only.</p></li>
<li><h3>Save a decision</h3><p>Choose <strong>APPROVED</strong> or <strong>REJECTED</strong>, enter a reason of 1–1,000 characters, and select <strong>Save review</strong>. Validation-REJECTED records cannot be approved. Resolve warnings from business evidence; reject or escalate unresolved issues.</p><p class="inline-note"><strong>Approval records your review. It does not release an order.</strong></p></li>
<li><h3>Confirm it saved</h3><p>Look for the saved message and updated review version. Return through <strong>Results</strong> and refresh before relying on displayed review status.</p></li>
<li><h3>Check the history</h3><p>Select <strong>History → Load / refresh history</strong>; use <strong>More history</strong> when enabled. Confirm the decision and keep the Request ID. The current audit actor is the shared development connection, not your individual sign-in.</p></li>
</ol>

**You are finished when** the saved decision appears in history. The existing authorized production process remains separate.

### If something goes wrong

<details markdown="1" class="recovery">
<summary>Submission timed out or the outcome is unknown</summary>

Keep the original text and the **source ID** shown in the message. Select **Load recent requests**, then **More requests** if needed, and match that source ID. Open the matching request if found. If absent, ask the owner to confirm it was not created before selecting **Allow new submission**. A timeout does not mean nothing was saved.
</details>

<details markdown="1" class="recovery">
<summary>A record is REJECTED or REQUIRES_REVIEW</summary>

Read the issue and obtain authoritative corrections. For invalid input, submit corrected source as a **new intake** and keep both Request IDs. Do not trim or rebuild the canonical string. For a warning, review the evidence; reject or escalate if it remains unresolved.
</details>

<details markdown="1" class="recovery">
<summary>A review did not confirm, or another review changed the record</summary>

For an unknown review outcome, stay on the record and select **Retry same command** when enabled. Keep the retained decision and reason unchanged. For a version conflict, select **Reload after conflict**, inspect the current review and retained reason, then decide again if appropriate.
</details>

<details markdown="1" class="recovery">
<summary>Results will not load, or the app was closed</summary>

After service recovery, retry the relevant load/refresh action. Treat retained rows as potentially stale. If the app restarted, reconcile recent requests and history: unsaved input and pending commands are held in memory. Give support the Request ID, record number, approximate time and visible error; exclude passwords and unredacted order screenshots.
</details>

<details markdown="1" class="diagram-detail">
<summary>See the operator flowchart</summary>

![The same operator journey, with recovery branches.](diagrams/03-current-user-sop.svg)
</details>

## Understand the workflow

Three different questions keep the workflow clear:

<div class="terms">
<p><strong>Validation</strong><br>Does the record pass format and business-rule checks? A request can contain records with different results.</p>
<p><strong>Review</strong><br>What did the reviewer decide, and why? The original evidence stays intact.</p>
<p><strong>Delivery</strong><br>Was an order handed off and acknowledged? This capability is proposed for Phase 2.</p>
</div>

Today, the app uses the existing solution, custom connector and gateway to reach a laptop API and local PostgreSQL. The parser preserves accepted positions and pads eligible records to 80 characters. It does not invent business data or check production stock/address references.

The separate manual process loads raw MILS staging, checks references and duplicate orders, and writes directly to the existing order table. The downstream flow remains unchanged; it was not exercised by the app's synthetic checks.

<details markdown="1" class="diagram-detail">
<summary>See the current functional flow</summary>

![Current development workflow and separate manual production path.](diagrams/01-current-functional.svg)
</details>

<details markdown="1" class="diagram-detail">
<summary>See the current technical architecture</summary>

![Current cloud connector, development laptop API and local PostgreSQL.](diagrams/02-current-architecture.svg)

Seven authenticated API operations support intake, request lookup, results, reviews and history. Basic authentication identifies the development connection. The API enforces the approved local database boundary. Publishing the app alone will not host the API, add per-user audit identity or enable Azure SQL.
</details>

**Still to verify:** accessibility/layout, canvas conflict and outage recovery, multi-page navigation, and shared-user authorization. The underlying API retry/conflict cases have standalone test evidence; that does not complete UI acceptance.

## Phase 2: two production periods

**Planning assumption: the app is published.** Keep the same operator journey and existing app lineage while qualifying production hosting, identity and one delivery route.

<div class="periods" markdown="1">

### 1 · Use existing Azure SQL

Move the API off the development laptop; add individual-user authorization, a SQL Server persistence adapter, live reference checks and controlled release. Begin with a bounded pilot using existing SQL capacity.

**Ready when:** API/UI failure paths, duplicate prevention, restore drills and operator acceptance pass. This requires implementation, not a connection-string swap.

### 2 · Move to accepted PostgreSQL

Retain the app/API contract. Migrate records, review history, audit identities and pending release commands; qualify database behavior and downstream acknowledgements. Switch production ownership once.

**Target:** December 31, 2026, subject to migration acceptance. The proposed Stage and Production services share one VM; that is isolation, not high availability.
</div>

### Three decisions come first

1. **Confirm SQL authority.** Migration records describe a freeze while the operating plan still uses SQL. Reconcile this before writes; new SQL activity requires an updated accepted migration baseline.
2. **Choose one delivery route.** Direct SQL handoff is the estimating baseline; the earlier Rainbow CSV/FTP proposal remains unresolved. Do not release the same order through both.
3. **Approve production ownership.** Set identities, hosting, workload limits, backup/recovery targets and the people responsible for acceptance.

<details markdown="1" class="diagram-detail">
<summary>See the Azure SQL architecture</summary>

![Proposed Azure SQL production architecture and controlled release boundary.](diagrams/04-phase2-azure-sql.svg)
</details>

<details markdown="1" class="diagram-detail">
<summary>See the future review → release → acknowledgement flow</summary>

![Proposed release flow; these controls do not exist in the current app.](diagrams/05-phase2-functional.svg)

A future release action needs a current approval, live reference checks, the right role and a durable command ID. Reconcile an uncertain outcome using that same command. A database commit or legacy SENT flag does not prove shipment; observe the agreed downstream acknowledgement separately.
</details>

<details markdown="1" class="diagram-detail">
<summary>See the PostgreSQL architecture</summary>

![Proposed PostgreSQL production after migration and operator acceptance.](diagrams/06-phase2-postgresql.svg)
</details>

### Two clocks, one handover

**Before cutover:** two months of controlled qualification while SQL remains authoritative. Start by October 31 for a full window ending December 31; late readiness moves the date unless the owner revises the gate.

**After PostgreSQL acceptance:** retain frozen SQL for 30 stable days before a separate retirement decision. A December 31 launch carries retention into January 2027. End-Q4 retirement would need acceptance around December 1.

<details markdown="1" class="diagram-detail">
<summary>See the transition timeline</summary>

![Qualification, one writer switch and stabilization are separate steps.](diagrams/07-phase2-transition.svg)
</details>

<details markdown="1" class="planning-detail">
<summary>Capacity, cutover and recovery: the essentials</summary>

**Measure before scaling.** Record peak users, batch size, API latency, lock waits, database CPU/IO, backlog and growth. For Azure SQL, test twice the measured expected peak; tune batches, queries and pools before buying capacity. Re-run the suite on PostgreSQL and address its indexes, pools and maintenance from evidence. These are proposed checks, not current service guarantees.

**Cut over in order:** baseline → rehearse → stop all writers → capture → reconcile → switch once → observe. Include new app/audit/release objects in the migration scope. Reconcile pending commands, qualify downstream connections, fence old SQL writers, and retain independently tested backups.

**Recover without losing new work.** Before PostgreSQL production writes, a validated return to the frozen SQL baseline is possible. After new PG writes, pause and reconcile those changes or repair PG. A blind connection switch to stale SQL risks loss and duplicate orders.
</details>

**Next work:** finish canvas acceptance and resolve the three decisions, then implement the Azure SQL adapter against a non-production target. Production deployment remains a separate accepted release.

## About this edition

Version **1.1.0** · Public reading edition · Evidence dated **September 23, 2026**.

Current claims come from recorded canvas execution, source controls and API tests. The manual route comes from the September 21 legacy review; migration assumptions come from the September 3 migration master and accepted roadmap. This edition does not re-inspect the tenant or production database. The implementation team retains detailed evidence and engineering decisions separately.

All seven charts are embedded. Expand a chart to read it, use **View larger** to zoom, or download its SVG. The HTML works offline; print includes expanded details. This documentation release does not publish or install the Power App.
