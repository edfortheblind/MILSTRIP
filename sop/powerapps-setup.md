# MILSTRIP app and database administration

**September 24, 2026.** The Stage/Prod runtime and configuration screen are
implemented. The tenant confirmed **Publish successful** for Stage at
**1:01:57 PM** and Prod at **1:15:52 PM**; both are in the existing MILSTRIP
solution. Published-player access is blocked by the current account's Power Apps
license prompt. Stage has Studio runtime evidence against local PostgreSQL;
Prod is disabled, and Azure SQL has no runtime acceptance yet. Use the
[illustrated operator SOP](../docs/operations-guide/index.html) for intake and review.

## Existing resources

| Resource | Configuration |
|---|---|
| Environment and solution | Existing Default environment; MILSTRIP solution, TAB publisher |
| Stage app | Published `MILSTRIP Stage`, renamed from `MILSTRIP Intake Dev`; app ID `7f1b64d0-d51a-4ec8-84ad-2b18fe8c2f82` |
| Prod app | Published `MILSTRIP Prod` in the same solution; separate Prod connection and fixed expected environment |
| Connector | Existing `MILSTRIP Local Dev API`; seven operations |
| Gateway | Existing `MILSTRIP-DEV-LAPTOP`; standard gateway, Central US |
| API | `http://127.0.0.1:8000/api/v1`; runs beside the gateway |
| Active database | Local PostgreSQL, `trav3pl-psqldb-stage`; application schema `milstrip_app` |
| Runtime configuration | Protected, ignored `.cred/runtime.json`; loaded once at API startup |
| Stage API verifier | `.cred/api-credential.json` |
| Prod API verifier | `.cred/api-prod-credential.json`; separate username and password |

The connector and gateway remain shared. Each app uses its own connection;
authenticated API credentials select the fixed database profile. App names,
headers and operator input cannot select a destination. Prod remains disabled
until its independent target is configured and verified.

Publishing the canvas app does not host the API or database. Laptop operation
requires the laptop, gateway, API and database to remain available. A database
move alone leaves the API on its current host.

## Resolve player access before rollout

Opening the published player displayed **no current Power Apps plan** and an
offer to start a free trial. The owner assigned licensing to IT; no trial was
accepted. Have IT verify the intended
users' Power Apps entitlement, app sharing and connector access before operator
acceptance. Publication is verified; a successful published-player session is
not yet verified. Studio test evidence does not establish player access.

## Start the API

Use an authorized account on the API host. Keep passwords and connection
strings out of Power Apps formulas, source files, screenshots and support messages.

```powershell
.\scripts\Start-LocalApi.ps1
```

The launcher requires valid runtime configuration and both credential verifier
files. It refuses an occupied port; stop the identified old API before restarting.
The existing gateway continues to reach the API through loopback HTTP. Do not
replace that host with the database server's address.

## Change PostgreSQL or Azure SQL configuration

Full reference: [Database configuration](../docs/RUNTIME_CONFIGURATION.md),
including TLS requirements, identity checks, provisioning and rollback.

1. Obtain the destination, database name, database identity and trusted server
   certificate from IT. Confirm whether this is **Stage** or **Prod** and whether
   existing application history must move. Configuration does not migrate data.
2. On the API host, open the configuration screen:

   ```powershell
   .\scripts\Configure-Runtime.ps1
   ```

3. Select **App environment** (`stage` or `prod`) and **Database provider**
   (`postgresql` or `sqlserver`). Set a non-sensitive **Display label**.
4. Paste the connection string into **Replacement connection string**. It stays
   masked. Leaving it blank retains the saved string; changing provider requires
   a replacement. **Current saved target** shows only host and database.
5. Select **Test connection**. It checks access, required application tables and
   environment identity without modifying data. An empty destination needs
   separately approved application-schema provisioning before it can pass.
6. Select **Enable this environment**, then **Save pending configuration**.
   A changed enabled destination requires a successful test. Stage and Prod
   cannot point to the same database or share a credential verifier.
7. Stop new submissions, record the change, and restart the shared API. Saving
   alone does not activate a new destination. Verify **GetHealth** for each
   connection: `environment`, `provider`, `target_label`,
   `configuration_revision` and `ready` must match the approved configuration.
8. Run a labeled synthetic intake and review in the intended environment. Read
   back the receipt, review and audit event. Confirm the other environment stayed
   unchanged. Retain or remove that test only according to its approved test plan.

Remote PostgreSQL requires hostname-verified TLS. Azure SQL uses Microsoft ODBC
Driver 17 or 18, encrypted transport and server certificate validation. The
screen rejects unsupported options and unverified remote destinations.

For a database move, reconcile requests, records, reviews, audit history and
environment identity before activation. Stop writers during the switch. A
rollback after new writes must preserve those writes; do not simply restore an
old string. Existing Azure SQL operational processes and the recorded SQL freeze
require approval before any new application writes.

## Maintain the two apps

1. Open **MILSTRIP Stage** in the existing MILSTRIP solution; retain its app ID.
   Keep the separate **MILSTRIP Prod** app in this solution. Do not duplicate
   the connector or gateway.
2. Bind each app to its environment's connection. Match the connection identity
   and actual app usage; identical display names are insufficient. Keep the
   connector's HTTP host `127.0.0.1:8000`, base `/api/v1` and gateway selection.
3. Refresh the connector definition from the current generated seven-operation
   contract when API response fields change. Verify **GetHealth** before editing
   formulas that use the new fields.
4. Preserve each app's fixed expected environment. Stage credentials were
   explicitly rejected by the Prod environment check; the selected Prod
   connection reports its disabled profile. Verify this isolation after changes.
5. Save and test the Stage draft. Verify successful intake, rejected-record handling,
   review, receipt and history; cover the changed behavior and its failure path.
6. Publish the verified Stage version. Promote the accepted canvas changes to
   Prod while retaining Prod's expected environment and connection. Save, publish
   and open the player version to verify the published result.
7. Record the published versions and sharing permissions. App publication does
   not automatically grant access to every user or configure their connections.

Both apps share one API implementation. API changes, connector changes and API
restarts can affect both environments. Separate canvas versions do not provide
an isolated backend deployment; schedule backend changes accordingly.

## Resolve connection failures

| Symptom | Action |
|---|---|
| Published app asks for a Power Apps plan | Have IT verify licensing, sharing and connection access. Do not treat publication or Studio access as evidence that the player is usable. |
| Connector test works; app returns 401 | Inspect the connection the app actually uses. Update that connection's dedicated API credential and preserve its gateway. Do not assume matching display names identify the same connection. |
| Configuration test fails | Check the destination, database identity, trusted certificate, provisioned schema and environment marker. Test does not create missing objects. |
| Health reports disabled or unavailable | Check the selected profile and API startup configuration. Never redirect Prod to Stage to bypass the failure. |
| Save reports a revision conflict | Reopen configuration, inspect the latest saved target, and reapply the intended change. |
| Submission outcome is uncertain | Preserve the source ID and reconcile recent requests before allowing a new submission. See the operator recovery procedure. |

## Changes and evidence

Place the forthcoming central change document in [inbox](../inbox/README.md).
Its contents remain local until reviewed. Record accepted requirements and test
evidence before promoting a change; depositing a file does not activate it.

The retained September 24 runtime test remains in PostgreSQL:
`1d0c784d-c3bf-495c-928c-0b66687a58a4`. Use the
[read-only result query](../db/queries/retained_runtime_2026-09-24.sql).
The Stage publication check also remains saved as request
`ff3f3cb5-04f5-4135-af74-f8db41962673`: two records, one APPROVED review and
two audit events. The illustrated SOP uses this run's four canvas captures.
App approval still records a review only; SQL handoff, CSV transport and downstream
receipts remain separate implementation work.
