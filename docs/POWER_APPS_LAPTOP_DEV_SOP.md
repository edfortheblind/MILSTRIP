# SOP — Power Apps development with the MILSTRIP backend on Ed's laptop

**Owner:** Ed Lopez. **Prepared:** 2026-09-23. **Purpose:** configure the human-owned
accounts, workspace and gateway, then hand implementation back to the coding agent.

## 1. What we are setting up

**Current handoff update (2026-09-23):** the owner completed setup in the
organization's existing Default environment, created the MILSTRIP solution and
connector, and registered MILSTRIP-DEV-LAPTOP. GetHealth passed through the
gateway using HTTP to `127.0.0.1:8000`. Keep those resources; do not repeat the
Developer-environment creation steps below. The connector export is in
`powerapps/connectors/`. API authentication, application actions and PAC access
remain pending; the passing test used a temporary health-only endpoint.

Your laptop remains the development host for Python, FastAPI and PostgreSQL.
Power Apps still needs a Power Platform cloud environment to hold its app,
solution, custom connector and connections. That environment is a development
workspace; it does not replace your laptop or require moving MILSTRIP tables.

Recommended local development path:

```text
Your work account signs in to Power Apps
                    |
Power Apps canvas app + custom connector [Power Platform DEV workspace]
                    |
           Microsoft gateway relay
                    |
       Standard on-premises data gateway [YOUR LAPTOP]
                    |
        http://127.0.0.1:8000/api/v1/... [YOUR LAPTOP]
                    |
        PostgreSQL localhost:5432 [YOUR LAPTOP]
        trav3pl-psqldb-stage / milstrip_app
```

The gateway provides the cloud-to-local bridge. Its external connection is
outbound; this design does not require a public API tunnel, router forwarding,
or exposing PostgreSQL. `127.0.0.1` means the gateway computer, so the gateway
must be installed on this same laptop for this design. Gateway/environment
regions must match. [Microsoft gateway architecture and administration](https://learn.microsoft.com/en-us/power-platform/admin/wp-onpremises-gateway).

Power Apps will host the user interface when deployed. PostgreSQL will host the
database. The Python API will still require an application host; Power Apps
does not execute this FastAPI process. Selecting that future API/database host
is deferred. The current task is entirely laptop-based backend development.

**Handoff milestone:** your cloud workspace, solution, gateway and authenticated
local CLI are ready. A working authenticated connector is the next implementation
task for me, not a prerequisite you must somehow solve first.

## 2. Existing state and names to use

The repository already contains the local API, migrations 001-005, review/read
endpoints and a verified 139-test baseline. Keep those files in this workspace;
some recent implementation files are not yet committed. Do not replace the
workspace by downloading an older GitHub copy.

During the preparation check, `pac` was not discoverable on the shell PATH and
the standard gateway service `PBIEgwService` was not detected. `dotnet` exists,
but `dotnet --list-sdks` returned no SDK entries. This is a detection snapshot,
not proof that no alternate CLI installation exists.

Use these proposed names, or record your existing equivalents:

| Item | Value |
| --- | --- |
| Power Platform environment display name | `MILSTRIP Dev` |
| Environment type | Developer |
| Solution display name / unique name | `MILSTRIP` / `MILSTRIP` |
| Publisher name / prefix | `TAB Development` / `tab` |
| Gateway name | `MILSTRIP-DEV-LAPTOP` or another tenant-unique name |
| PAC authentication profile | `MILSTRIP-DEV` |
| Future custom connector | `MILSTRIP Local Dev API` |
| Future canvas app | `MILSTRIP Intake Dev` |
| API origin / base path | `http://127.0.0.1:8000` / `/api/v1` |
| Local database | Existing `trav3pl-psqldb-stage` |

Use synthetic records during development. The database remains local, but API
requests and responses used by a canvas app pass through Power Platform.

## 3. Establish the Power Platform development workspace

### 3.1 Use the correct account and license

Sign in with your existing TAB work account. Use that same tenant/account for
the maker portal, gateway registration and PAC login. Keep the organization's
existing MFA and any federated sign-in; no AD FS change is needed for this SOP.

For individual development, the Power Apps Developer Plan includes custom
connectors and access through an on-premises gateway. It is for development and
testing, not production operation. Tenant policy can restrict enrollment or
environment creation. A Microsoft 365 account alone is not confirmation of the
required entitlement. [Developer Plan capabilities](https://learn.microsoft.com/en-us/power-platform/developer/plan).

### 3.2 Create or select the environment

1. Open [the Developer Plan signup guide](https://learn.microsoft.com/en-us/power-platform/developer/create-developer-environment)
   and follow its signup link using your work account, if you do not already
   have a suitable developer environment.
2. Open [Power Apps](https://make.powerapps.com). Use the environment selector
   to choose the developer environment created for you. Do not accidentally
   build in the tenant's shared Default environment.
3. Open [Power Platform admin center](https://admin.powerplatform.microsoft.com).
   Find **Environments** under **Manage** or the environment-management area.
   Select the developer environment. Rename its display name to `MILSTRIP Dev`
   if permitted; keeping its existing display name is also acceptable.
4. If creating another environment instead, choose **New**, use the proposed
   name, select **Developer**, and select your organization's allowed region.
   Follow the Dataverse provisioning prompts. Wait for the environment to be ready.
5. Record its **environment ID**, **environment URL**, **region**, **type** and
   **tenant ID**. The URL should be the Dataverse organization URL shown in the
   environment details, not the browser's long maker-portal URL.

Keep the developer environment unmanaged unless tenant policy requires otherwise;
Managed Environments have additional license requirements. Dataverse here holds
solution/platform metadata. We are not migrating MILSTRIP operational data into
Dataverse. [Environment creation](https://learn.microsoft.com/en-us/power-platform/admin/create-environment),
[Developer Plan restrictions](https://learn.microsoft.com/en-us/power-platform/developer/plan).

**Pass:** you can select the intended environment in the maker portal and open
its Solutions area. If tenant policy blocks creation, request an approved
development environment from your administrator; do not create an unrelated
personal tenant to bypass it.

## 4. Configure your maker identity and create the solution

### 4.1 Verify environment permissions

You need permission to create canvas apps, solution components, custom
connectors and connections in this development environment. For a Dataverse
environment, verify your environment-scoped roles with its administrator:
Environment Maker plus the appropriate customization privileges, commonly
System Customizer, or existing System Administrator rights in your own isolated
developer environment. Do not request tenant Global Administrator solely for
this project. [Microsoft's role distinctions](https://learn.microsoft.com/en-us/power-platform/admin/database-security).

Also confirm that the applicable data policy permits this custom connector and
gateway route. If blocked, ask the administrator for a narrowly scoped DEV
exception or approved policy configuration. Do not disable the organization's
data policies. [Connector classification](https://learn.microsoft.com/en-us/power-platform/admin/dlp-connector-classification).

Suggested request to your administrator, if needed:

> Please enable development of the MILSTRIP canvas app in our approved Developer
> environment, with solution/custom-connector permissions and use of a standard
> gateway installed on my laptop. The API and PostgreSQL remain local. Please
> confirm the tenant, environment region, developer entitlement, maker/customizer
> access and applicable connector policy. No production access is requested.

### 4.2 Create the solution container

In the selected environment, choose **Solutions → New solution**. Use display
name `MILSTRIP`, unique name `MILSTRIP`, version `0.1.0.0`. Select the existing
TAB publisher or create `TAB Development` with prefix `tab`. Save and open the
solution. Work inside this unmanaged solution so its components can be moved
together later. [Create a solution](https://learn.microsoft.com/en-us/power-apps/maker/data-platform/create-solution).

An empty solution is sufficient at handoff. Do not build screens, import tables,
or manually copy API fields now. If you already created a canvas app, record its
name/ID and leave it in place; do not delete it.

**Pass:** the solution opens and you can see its component creation controls.

## 5. Install and register the gateway on this laptop

1. Open Microsoft's [gateway installation guide](https://learn.microsoft.com/en-us/data-integration/gateway/service-gateway-install)
   and use its **standard gateway** download. Personal mode is for Power BI
   and is not the mode for this Power Apps setup.
2. Install on this laptop using the required local administrator privileges.
   If a standard gateway already exists, inspect/reuse it with its owner instead
   of installing another standard instance.
3. Sign in with your TAB work account. Register a new gateway on this computer
   and use `MILSTRIP-DEV-LAPTOP` or a tenant-unique variant.
4. Set a recovery key and store it in your approved password manager. It is a
   gateway recovery secret, not an API password; do not put it in the handoff.
5. Confirm the gateway cloud/region matches the development environment, then
   finish registration. Verify the gateway reports **Online** and is visible
   to your work account in Power Platform's gateway-management area.

For this laptop-only DEV choice, keep the laptop awake, powered and connected
during testing. Microsoft recommends always-on gateway hosts; sleeping or
disconnecting this laptop deliberately makes the development route unavailable.
Move the gateway/backend to an appropriate host only when deploying later.

In a normal PowerShell window:

```powershell
Get-Service -Name PBIEgwService
```

Expected: the service exists and is Running. Record the gateway name, cluster/ID
if displayed, machine name, region and online status. The default Windows service
identity is separate from your maker login; it does not need PostgreSQL access
because it will call the API. [Gateway administration](https://learn.microsoft.com/en-us/power-platform/admin/wp-onpremises-gateway).

**Pass:** service running and gateway online in the correct tenant/region.
This proves the gateway registration, not yet an end-to-end API call.

## 6. Verify the local API access path

Open this repository in VS Code and a PowerShell terminal at its root. Keep the
existing PostgreSQL instance and approved local authentication arrangement.

```powershell
Test-Path .\.venv\Scripts\python.exe
Test-NetConnection 127.0.0.1 -Port 5432

# Reuse the configured URL. This fallback contains no password and relies on
# the workstation's existing approved PostgreSQL authentication.
if (-not $env:MILSTRIP_DATABASE_URL) {
    $env:MILSTRIP_DATABASE_URL = 'postgresql://TabAdmin@localhost:5432/trav3pl-psqldb-stage'
}

& .\.venv\Scripts\python.exe -m uvicorn api.app:app --host 127.0.0.1 --port 8000 --no-proxy-headers
```

The last command runs in the foreground. Leave that terminal open while testing.
In a second terminal:

```powershell
Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/health'
```

Expected: `status` = `OK`, `database` = `AVAILABLE`. Open
`http://127.0.0.1:8000/docs` in your browser and confirm the operator routes exist.
Do not paste the database URL into chat if your configured version includes a
password. A DEGRADED health response can still have HTTP status 200; inspect the
JSON fields, not only the HTTP status.

The future connector settings are:

| Field | Development value |
| --- | --- |
| Gateway | The gateway installed on this laptop |
| Scheme | HTTP, for the same-machine loopback hop only |
| Host | `127.0.0.1:8000` |
| Base URL | `/api/v1` |
| Health operation relative path | `/health` |
| Authentication | Basic authentication, implemented by me after handoff |

The gateway-to-API HTTP hop stays on this machine; it is not permission to use
Basic authentication over cleartext LAN/public HTTP. If the gateway must run on
another computer or policy requires HTTPS locally, record that constraint at
handoff so I can configure a trusted TLS endpoint before connecting it.

Do not open inbound ports 8000 or 5432 for the cloud, bind to `0.0.0.0`, add a
public tunnel, or create a direct Power Apps PostgreSQL connection for this path.
The API owns validation, review and database access.

**Pass:** local health is OK and the API listens on loopback. Stop it with
Ctrl+C when finished, or report that it is still running at handoff.

## 7. Configure identity correctly for this development stage

There are four distinct identities. Keeping them separate avoids unnecessary
Entra registrations and prevents a development setting from being mistaken for SSO.

| Identity | Configuration now | What it grants |
| --- | --- | --- |
| Your TAB work account | Sign into maker portal, gateway registration and PAC using existing MFA | Development workspace/solution access |
| Gateway Windows service | Keep its approved installation identity | Runs the local bridge; not database authorization |
| API development account | Reserve username `milstrip-dev-ed`; I implement its dedicated password verification after handoff | One-maker synthetic API testing |
| PostgreSQL role | Reuse existing local database configuration | Backend access to `milstrip_app` |

For the proposed gateway route, use Basic authentication for the dedicated API
development account. Microsoft's connector FAQ excludes API-key authentication
on the on-premises gateway; this is not an API-key setup. Do not select Windows
authentication unless we actually implement a compatible Windows-auth endpoint.
[Connector authentication support](https://learn.microsoft.com/en-us/connectors/custom-connectors/faq).

**No new Entra API app registration, client secret, redirect URI or AD FS
configuration is required before this handoff.** Existing work-account sign-in
is used for the platform. API authorization for this local single-maker path
will be a separate dedicated development credential, not your Microsoft password.

Current code does not yet validate Basic credentials. Its
`MILSTRIP_LOCAL_REVIEWER` setting only supplies a local test actor and checks
loopback access. Setting it is not authentication. I must add credential
validation to the data/review API and derive the development actor from the
authenticated account before enabling the connector connection.

Do not create a No Authentication gateway connection as a workaround: Microsoft
documents that gateway selection is not supported for anonymous custom
connectors. [Canvas connector authentication](https://learn.microsoft.com/en-us/power-apps/maker/canvas-apps/connections-list).

No secret is required in your handoff. I can prepare a dedicated development
credential through a local protected configuration workflow when implementing
authentication. If the connector UI later requires you to enter it, use the
locally stored credential; never send your work password, a token or a gateway
recovery key in chat.

This first connection represents one developer. A shared gateway connection
does not automatically prove the identity of each person running an app.
Per-user delegated identity and production reviewer roles are a later acceptance
step. Do not share this development connection as an audited multiuser system.
[Gateway credential behavior](https://learn.microsoft.com/en-us/power-apps/maker/canvas-apps/gateway-reference).

## 8. Install PAC CLI and sign in from the laptop

This is the main enabler for me to continue without repeatedly asking you to
export files. Use the same Windows user account under which this workspace and
the coding agent run.

### 8.1 Install a shell-accessible CLI

Use the **Windows MSI** installation route in Microsoft's
[Power Platform CLI installation guide](https://learn.microsoft.com/en-us/power-platform/developer/cli/introduction).
Install, then reopen PowerShell/VS Code and run:

```powershell
Get-Command pac | Select-Object Source
pac
```

Record the executable path and displayed version. A VS Code-only installation
can work, but its CLI might not be on a normal shell PATH; provide the executable
path if that is your setup. Our handoff requires a CLI the agent can invoke.

Alternative, only if a supported .NET SDK is installed:

```powershell
dotnet tool install --global Microsoft.PowerApps.CLI.Tool
```

The current laptop check did not list an SDK, so prefer the Windows installer
unless you deliberately install one. [Official .NET-tool procedure](https://learn.microsoft.com/en-us/power-platform/developer/howto/install-cli-net-tool).

### 8.2 Create an explicitly scoped login profile

Replace these nonsecret placeholders with values recorded in Step 3:

```powershell
$milstripEnvironmentUrl = 'https://YOUR-DEV-ORG.crm.dynamics.com'
$milstripTenantId = 'YOUR-TENANT-GUID'

pac auth create --name MILSTRIP-DEV --environment $milstripEnvironmentUrl --tenant $milstripTenantId --deviceCode --cloud Public
pac auth select --name MILSTRIP-DEV
pac auth who
pac solution list --environment $milstripEnvironmentUrl
```

Complete the browser/device-code sign-in yourself with the same work account
and its MFA. Verify the returned identity/environment and that the solution list
contains `MILSTRIP`. For GCC/GCC High/DoD/China, record the actual cloud and use
its matching PAC cloud option/portal; do not force Public. If device-code login
is disallowed by tenant policy, retry interactive login without `--deviceCode`.
[PAC authentication](https://learn.microsoft.com/en-us/power-platform/developer/cli/reference/auth).

Do not run `pac auth token` for the handoff. No token export, service-principal
password or new tenant-wide permission is needed. PAC access remains subject to
your permissions and session expiry; renewed MFA may still need you later.

**Pass:** the local CLI identifies the intended DEV account/environment and can
list its solution. This proves authenticated read access; actual connector and
solution write privileges will be checked when I create those components.

## 9. Stop here and hand the work back

You do not need to create a connector, connection, connection reference or
finished canvas app first. Creating them before authentication and the connector
schema are ready adds rework.

Copy [the handoff template](templates/POWER_APPS_DEV_HANDOFF.template.md) into
`local-discovery/powerapps-dev-handoff.md`, which is already ignored by Git.
Fill its nonsecret fields. Confirm:

- The correct Developer environment is ready and has Dataverse/solution support.
- The `MILSTRIP` solution exists and your permissions/policy allow development.
- The standard gateway is installed on this laptop, online, and region-matched.
- API health is OK on `127.0.0.1:8000` and PostgreSQL remains local.
- PAC is callable and `MILSTRIP-DEV` is authenticated to the intended environment.
- You recorded whether the API is running and any unresolved administrator blocks.

Then send:

> Laptop Power Apps prerequisites are ready. Read
> `local-discovery/powerapps-dev-handoff.md`. Continue the local authentication,
> custom connector and canvas-app implementation in the listed DEV environment
> and MILSTRIP solution. Keep the API and PostgreSQL on this laptop.

An incomplete prerequisite is not a reason to guess a value. Mark it pending and
include the error text without credentials; the remaining local work can continue.

## 10. Work I take over after handoff

1. Verify the PAC identity, target environment, solution and gateway against the
   packet before making cloud changes.
2. Implement and test dedicated local API authentication, protecting data and
   write routes; bind the development reviewer to the authenticated account.
3. Produce a connector-specific **OpenAPI 2.0** definition and gateway properties.
   The existing `operator-api.openapi.json` is a FastAPI OpenAPI 3.1 reference,
   not an import-ready Power Apps connector file. [Supported connector formats](https://learn.microsoft.com/en-us/connectors/custom-connectors/faq).
4. Create/update the connector in the specified solution using the authenticated
   tooling. PAC supports connector creation, download and update.
   [PAC connector commands](https://learn.microsoft.com/en-us/power-platform/developer/cli/reference/connector).
5. Bind the gateway connection and verify health, unauthenticated rejection,
   synthetic intake, pagination, review retries/conflicts and audit history.
6. Generate a development canvas app from the solution-aware connector, then
   build/refine intake, results, review and history behavior. Export versioned
   solution artifacts and retain deterministic backend tests.

There is a real automation limit: Microsoft's `pac canvas create` can generate
an `.msapp`, but its documented workflow still requires Studio import and adding
the connector reference. Canvas pack/unpack is deprecated; it is not a reliable
promise of unattended designer round-tripping. I can do the backend, schema,
connector and supported CLI work independently with the authenticated profile.
MFA, consent, credential entry and Studio-only actions may still need you unless
an authorized browser automation path is available. [Canvas CLI capabilities](https://learn.microsoft.com/en-us/power-platform/developer/cli/reference/canvas).

## 11. Troubleshooting and daily start/stop

| Symptom | Check/action |
| --- | --- |
| No Developer environment/signup blocked | Work account, Developer entitlement and tenant environment policy; ask the admin |
| Solutions/custom connector creation unavailable | Correct environment, Dataverse provisioning and environment-scoped customization roles |
| Gateway installed but not selectable | Standard mode, same tenant, same region, account access and connector auth type |
| Gateway offline | Laptop power/sleep/network, Windows service and gateway network diagnostic; ask IT about required outbound access |
| Local health shows DEGRADED | PostgreSQL running and approved authentication available to the API process |
| `pac` not recognized | Reopen the shell; check install method/PATH and provide the actual executable path |
| PAC opens the wrong environment | Select `MILSTRIP-DEV`; verify with `pac auth who`; use explicit target environment arguments |
| Raw API JSON will not import as connector | Use the OpenAPI 2.0 connector artifact I prepare, not the current 3.1 runtime export |
| Review returns 503 in the current local build | Local reviewer may be unset; this is separate from the future Basic-auth implementation |
| Health succeeds with wrong Basic credentials before handoff | Current health/API code is not Basic-auth protected; it does not prove authentication works |
| Cloud call times out after handoff | Gateway status, selected gateway, API process, exact host/port/base path and same-machine loopback assumption |

For each development session: keep the laptop awake; check PostgreSQL and gateway
services; start the API using the agreed local configuration; verify health;
then open the app in the DEV environment. When stopping, save Studio changes,
stop the foreground API with Ctrl+C, and leave the registered gateway installed.
Closing the API or sleeping the laptop makes the development app's backend
unavailable; it does not deploy, delete or migrate anything.

When ready for deployment, package the app/connector solution, choose API and
PostgreSQL hosting, replace the local identity model, and change the environment's
connection configuration. Those are later steps, not prerequisites for this SOP.
