# MILSTRIP administration SOP

**Status: September 24, 2026 - Stage administration draft tested; publication and full acceptance pending.**

The existing published **MILSTRIP Stage** player is healthy and can read retained
results. The published **MILSTRIP Prod** player opens and reports an unavailable,
disabled database. Licensing is resolved for both. Prod remains disabled because
its database target and activation authority have not been confirmed.

The new **Configuration** and **Users** screens below are the deployment target.
They are not yet accepted in the published apps. This SOP distinguishes their
source behavior from the currently available host configuration tool. See the
[current evidence](delivery/IDENTITY_ADMIN_STATUS_2026-09-24.md) for the release boundary.

The existing Stage app now has six native draft screens, zero formula errors
and two literal-predicate warnings. The observed Stage broker calls succeeded,
and Configuration loaded its expected provider, label and revision. The direct
API data source was removed from that draft. Ed alone has active application
membership; the other five initial memberships remain pending. Prod draft
acceptance, broader sharing, broker-only cutover and new publication remain open.

## Access and responsibilities

Sign in with the existing Travis Association for the Blind Microsoft Entra
account. Realm discovery confirmed managed Entra SSO for `austinlighthouse.org`;
no new identity provider or AD FS deployment is required. A live directory probe
verified all six initial people as enabled internal members.

| Application role | Initial people | Permissions |
|---|---|---|
| Permanent Owner | Claude Furry (`claude.furry@austinlighthouse.org`); Mike Thompson (`mike.thompson@austinlighthouse.org`) | Intake, review, configuration and user administration |
| Admin | Ed Lopez, Kristen Fleming, Thomas Stivers, Shawn Hinkle | Intake, review, configuration and user administration |
| Operator | Added by an Owner or Admin | Intake and review |

Claude and Mike cannot be removed, disabled or demoted through the application.
Owner is not an assignable role. Directory disablement still blocks application access.
Application permissions do not create directory accounts or change tenant roles.

Ed's existing **Power Platform app Owner** permission is separate from his
**application Admin** role. The verified existing Owner grant permits viewing
without being changed. Other app users receive CanView and flow run-only rights,
including application Owners and Admins. Removing Ed's application access denies
API use immediately; platform cleanup can remain pending until IT transfers app
ownership. The application does not transfer ownership.

## Configure a database in the app - after deployment acceptance

Open the app for the environment being changed. Stage cannot configure Prod's
destination, and Prod cannot configure Stage's. Authorized administration remains
available when that app's business database is disabled or unavailable.

1. Open **Configuration**, then **Load configuration**. Check the environment,
   active target and revision.
2. Select `postgresql` or `sqlserver`, enter a short target label and set
   **Enabled**. Enter a replacement connection string in the masked field only
   when changing it. Blank retains the saved string; a provider change requires
   a replacement.
3. Select **Save draft**. This stores the proposal privately and clears the
   visible connection-string field. It does not activate or provision anything.
4. Select **Test draft**. A pass checks connectivity, the six application tables
   and the matching Stage/Prod identity. It does not establish write permissions
   or production readiness. A failed test does not change the active target.
5. Select **Apply draft**. Enabling a target requires a successful test of this
   exact draft by the same administrator, within its five-minute validity period.
   A stale revision or expired test is rejected; reload or test again.
6. Confirm **APPLIED**, reload configuration and check the app connection. Verify
   the expected environment and existing history before releasing it for use.

A saved draft locks its form. To change it, select **Discard draft**; this clears
the draft and test, restores the active settings and clears the replacement
field. Load configuration again if the active revision changed, then enter and
save the revised proposal. An expired test can be rerun for the unchanged draft.

Apply waits for that environment's active requests to finish, then changes its
saved active revision. The other environment can continue. Ordinary profile
changes do not require restarting the shared API; code deployments and process
restarts still affect both apps.

To move an enabled environment to a different database, first save and apply a
draft with **Enabled** cleared and the current target retained. Disabling does
not require a successful database test. Keep the environment disabled during
provisioning, migration and reconciliation. Then save the new destination, test
and apply it. No automatic fallback to another database is allowed.

If the result is unknown, use **Check command status**, then **Retry same
command** if needed. Do not submit a different change to replace an uncertain
one. Keep the app open: its retained command is held in session memory. Record
the displayed command ID before closing the app so the host administrator can
look up the durable result.

## Manage application users - after deployment acceptance

1. Open **Users** and select **Load users**.
2. For a new member, select **New user** and enter their complete
   `@austinlighthouse.org` sign-in name. For an existing member, select their row.
3. Choose **OPERATOR** or **ADMIN**, then **Save access**. The broker resolves
   additions against the tenant directory; an email suffix alone is insufficient.
4. Confirm **Access: active | Sharing: completed**. Pending access is not ready
   for use. The flow grants only the two app views and their run-only flows.
5. To revoke access, select the member and **Remove access**. The API denies that
   member immediately, even when platform cleanup remains pending. Removal also
   works after the directory account has been disabled or deleted.

For an unconfirmed result, select **Check command status** or **Retry sharing**.
Retry uses the existing command. Do not replace a pending command with another
access change. No sharing notification email is sent.

Sharing calls are paced across both apps to stay within the Management
connector's limit. A response timeout can occur while the flow continues; keep
the command and check its status. An uncertain Management call also holds a
shared connection permit, so other user changes may remain pending until the
host administrator resolves that call.

A failed or timed-out platform write can leave an unknown outcome. The server
keeps a lock for that target across both apps so an older Add cannot overtake a
newer Remove. Repeated clicks cannot clear it. The host administrator must inspect
the recorded plan, execution and flow run; establish that prior external actions
have stopped; read back current grants; and complete controlled recovery of the
recorded execution before starting another. Recovery uses the broker-only
callback with the original lease/execution identifiers and fresh grant readback;
the [implementation contract](delivery/IDENTITY_ADMIN_IMPLEMENTATION_CONTRACT_2026-09-24.md#5-membership-and-platform-sharing-reconciliation)
defines those fields. There is no automatic expiry, in-app force-unlock or
packaged host recovery wizard. Do not delete the lock or control file to bypass recovery.

## API-host setup and recovery

The source uses one private `.cred/control.json` after broker-only cutover. It
holds application permissions, protected owner identities, active profile
revisions, drafts and command outcomes. The old `.cred/runtime.json` is imported
once and is not a second active authority. These files are Git-ignored and
restricted by Windows permissions; this application does not encrypt them.

Before first cutover, the host command compares the imported profiles with the
selected legacy runtime while holding the configuration lock. If that source
changed or is missing, activation stops and leaves the current runtime intact.
Back up both private files and have the deployment lead reconcile the inactive
import, including existing drafts and test receipts, before retrying. There is
no automatic refresh; do not delete control state or discard reviewed drafts to
clear the error. Once control is active, restart and activation checks no longer
depend on the legacy runtime file.

Each app calls its fixed broker flow. Office 365 Users must be **Provided by
run-only user** for caller identification. Directory, sharing-management and
broker connections remain private to the deployment account. Stage and Prod use
distinct private broker credentials through the existing custom connector and
gateway. Neither broker credentials nor saved database strings are returned to
app users. Secure flow inputs and outputs must be verified in actual run history.

Run one API worker. After a process failure, restart from the authoritative
control state; a durable Apply is not undone by restarting. If saved and running
revisions disagree, the affected environment remains blocked until host recovery.
Never edit active JSON behind the running service or reopen legacy Basic access
to bypass an incomplete app deployment.

### Current host tool, before cutover

The existing Windows configuration tool remains the current pre-cutover path:

```powershell
.\scripts\Configure-Runtime.ps1
```

Select the environment and provider, enter the masked replacement string, test,
and **Save pending configuration**. Stop the identified MILSTRIP API after active
requests finish, then start it with `.\scripts\Start-LocalApi.ps1` and verify both
app connections. Both launchers select explicit `-ConfigFile` first, then
`MILSTRIP_RUNTIME_CONFIG_FILE`, then `.cred/runtime.json`. A configuration file
must reside directly inside `.cred`. The legacy tool is not the active-profile
editor after broker-only cutover and refuses to save in active control mode.
`-ControlFile`, then `MILSTRIP_CONTROL_FILE`, then `.cred/control.json` selects
the control authority. Keep launch, configuration and provisioning tools on the
same intended authority; an alternate legacy file cannot override active control.

### Provisioning and data moves

The DBA must approve the destination and create the database/runtime identity.
Schema provisioning is a separate host operation; Save, Test and Apply do not
create tables. The provisioning CLI selects the authoritative saved profile:
active control after cutover, otherwise the legacy runtime configuration. It
does not select an unapplied draft. For a new destination, save and apply it
with **Enabled** cleared first; it remains unavailable to business requests.
Confirm the CLI's printed target before a provisioning write:

```powershell
.\scripts\Initialize-ApplicationDatabase.ps1 -Environment prod
.\scripts\Initialize-ApplicationDatabase.ps1 -Environment prod -ProvisionApplicationSchema -ConfirmTarget '<exact preview target>'
```

This creates the five application data tables plus `environment_identity` in an
existing database, preserving compatible rows. It does not create a database,
relabel another environment, or modify operational shipment tables. An Azure SQL
production source is not authorized by this SOP; its freeze and deployment
approval remain separate.

Changing a connection string does not transfer intake, review or audit history.
Use an approved backup/restore or provider migration and reconcile IDs, counts,
canonical values, review versions, sequences and audit events. Preserve the
retained Stage tests. Returning to an old database after new writes requires
reconciliation; changing the string back alone is not data recovery.

### Connection formats

Enter actual values privately. Examples contain placeholders only.

```text
host=pg-stage.example.invalid port=5432 dbname=milstrip_stage user=DB_USER password='PRIVATE_PASSWORD' sslmode=verify-full sslrootcert=C:/Certificates/root-ca.pem
Driver={ODBC Driver 18 for SQL Server};Server=tcp:sql-stage.example.invalid,1433;Database=milstrip_stage;Uid=DB_USER;Pwd={PRIVATE_PASSWORD};Encrypt=yes;TrustServerCertificate=no;
```

Remote PostgreSQL requires verified TLS. Local loopback may use the existing
configuration. Service files, passfile/host-address overrides and session options
are rejected, including inherited `PGHOSTADDR`, `PGSERVICE`, `PGSERVICEFILE`,
`PGOPTIONS` and `PGPASSFILE`. SQL Server requires Microsoft ODBC Driver 17 or 18,
encryption and certificate validation. Live Azure SQL acceptance remains pending.

## Optional request to the domain administrator ? draft only

> Please provide these optional HTTPS redirects:
>
> - `milstrip.austinlighthouse.org` to [MILSTRIP Prod](https://apps.powerapps.com/play/e/default-9f5c0ace-0780-4b48-8c24-b08bb5149210/a/0aa02d8b-c7fa-42cc-87e8-6d287bd4c897).
> - `milstrip-stage.austinlighthouse.org` to [MILSTRIP Stage](https://apps.powerapps.com/play/e/default-9f5c0ace-0780-4b48-8c24-b08bb5149210/a/7f1b64d0-d51a-4ec8-84ad-2b18fe8c2f82).
>
> Please confirm certificate ownership and the service
> that will perform the redirects; a DNS record alone cannot redirect to the
> app's full path. Keep sign-in with our existing managed Entra tenant. No new
> SSO provider, federation or application password is requested. At the later
> approved VM move, please also reserve a separate internal API hostname and
> confirm its routing, certificate and gateway access. That API name is distinct
> from the user-facing redirect names.

This is a prepared request, not a submitted change. No DNS, redirect, hostname
or SSO-provider changes have been performed. Friendly links do not activate the
Prod database or establish production readiness.

Sources: [ADR 0006](adr/0006-user-identity-and-administration.md),
[broker flow source](../powerapps/flows/README.md),
[canvas administration source](../powerapps/canvas/broker/README.md),
[configuration service](../api/administration.py).
