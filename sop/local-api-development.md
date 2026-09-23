# Authenticated laptop API continuation

Use the existing Default environment, MILSTRIP solution, MILSTRIP Local Dev API
connector, MILSTRIP-DEV-LAPTOP gateway and app ID
`7f1b64d0-d51a-4ec8-84ad-2b18fe8c2f82`.

## Private credential setup

From a PowerShell terminal at the repository root:

```powershell
.\scripts\Set-LocalApiCredential.ps1
```

No virtual-environment activation is needed: the script uses `.venv` explicitly.
Enter a dedicated API username (also the development audit identity), then a new
password of at least 16 printable ASCII characters and its confirmation. Input
is hidden. Do not reuse the work-account password or send it in chat.

Only a salted PBKDF2-SHA256 verifier is saved under
`.cred/api-credential.json`; the directory allows the current
Windows user only. The plaintext password is never written by this setup.
Retain it privately for the connector connection. Re-running setup asks before
replacing an existing verifier; mismatched/short passwords permit three attempts.

The initial script's repeated `Set-Acl` call failed with `SeSecurityPrivilege`.
It now uses DACL-only `icacls` and verifies the resulting permissions. The fixed
permission step was executed twice successfully without elevation. Do not run
as administrator or weaken the folder permissions to work around that old error.

## Start the real API

```powershell
.\scripts\Start-LocalApi.ps1
```

Keep the terminal open. This binds HTTP 127.0.0.1:8000, disables forwarded-header
trust and access logs, and uses existing local PostgreSQL authentication. It
refuses to kill an occupied port. Identify and stop the prior development API
before restarting if port 8000 is occupied. The gateway runs separately.

After the owner confirmed configuration, the agent started this launcher in a
hidden background process and verified port 8000. Do not start a second copy
while it is running. Background stdout/stderr are in the private
`%LOCALAPPDATA%\MILSTRIP` log directory as `api.stdout.log` and `api.stderr.log`;
HTTP access logging is disabled. This is not an auto-start Windows service.

All `/api/v1` routes, including health, require Basic authentication. Missing or
wrong credentials return 401; valid credentials allow health/application calls.
The prior health-only process must not be used for these checks. A missing or
corrupt verifier returns 503, never unauthenticated access.

## Update the existing connector

1. Open **MILSTRIP Local Dev API → Edit → Swagger editor**. Replace the definition
   with `powerapps/connectors/MILSTRIP-Local-Dev-API.swagger.json`, then select
   **Update connector**. If available, **Update from OpenAPI file** can update this
   same connector. Do not choose New connector.
2. Retain HTTP, host `127.0.0.1:8000`, base `/api/v1`, Basic authentication and
   **Connect via on-premises data gateway**. Keep custom code disabled.
3. Fix/update the existing connection credentials privately to match setup.
   Retain **MILSTRIP-DEV-LAPTOP**. If credentials cannot be edited, a replacement
   connection to the same connector/gateway may be needed; do not recreate them.
4. Test GetHealth for 200/AVAILABLE, then ListIntakeRequests with limit 1. Use only
   synthetic text for CreateIntakeRequest. Retrieve its detail, records and audit.
5. Submit a review with current version and a new command UUID. Exact retry must
   return 200 with the same decision. A new command with stale version returns
   409. Invalid credentials must fail with 401. Share response status only.
6. Continue the saved app using `powerapps/canvas/README.md`; verify membership in
   the existing solution and save after App checker passes.

Local verification is separate from tenant acceptance. Basic identifies the
development connection, not each signed-in Power Apps user. Shared rollout,
operational writes and SQL Server retirement remain outside this increment.

## Diagnose a gateway 401 without exposing credentials

Run this from the repository terminal:

```powershell
.\.venv\Scripts\python.exe scripts\check_api_credentials.py
```

Enter the dedicated API username and password privately. The script calls only
the fixed loopback health endpoint, bypasses environment proxies, refuses
redirects, and prints a status/result without saving or displaying credentials.

- Local 200: the credential works. Update the saved connector connection with
  those same values, then refresh the Test tab and select that exact connection.
  The existing health-test connection may still contain its original unverified
  credential. If its credentials cannot be edited, create a replacement
  connection to the existing connector and MILSTRIP-DEV-LAPTOP gateway.
- Local 401: re-enter the credential or rerun private setup, then update the
  connector connection to match. Changing the verifier does not update a saved
  Power Platform connection automatically.
- Connection failure: confirm the loopback launcher is running.

Report the gateway response body's detail message only. `Invalid credentials`
means Basic credentials failed verification; `Authentication required` means
the API did not receive supported Basic credentials. Never share request headers.

## Authenticated gateway health accepted (2026-09-23)

The owner ran `check_api_credentials.py` privately and supplied its HTTP 200
result. The saved gateway connection still returned 401. The owner then followed
these steps: Test -> New connection, enter the same dedicated credential,
select MILSTRIP-DEV-LAPTOP, create the connection, refresh the Test connection
list, select the new connection and run GetHealth. The supplied screenshot shows
GetHealth success and HTTP 200 on the real authenticated API. Connector, gateway,
solution and environment were reused; only the saved connection was replaced.
The old connection was not deleted as part of these instructions.

The screenshot still shows **Operations (1)**. Update the existing connector
with `powerapps/connectors/MILSTRIP-Local-Dev-API.swagger.json` next. The local
artifact contains seven operations and its runtime projection check passed.
Gateway tests of application routes and Studio validation remain pending.

## Project credential folder

At the owner's request, project credential files now live in repository-root
`.cred/`. The supplied `milstrip-app cred.txt` and the API's `api-credential.json`
were moved there without displaying their contents. The folder and files have
current-user-only Windows permissions and are excluded from Git. An additional
ignore rule protects the original text filename if it is placed at the root again.

Setup, the runtime default and the launcher use `.cred/api-credential.json`.
The API was restarted after the move; passwords were not changed. Diagnostic
logs remain in `%LOCALAPPDATA%/MILSTRIP` because they are not credential files.
Do not relocate machine-wide PostgreSQL or tenant credential stores into this
project. This checkout is under OneDrive; Git exclusions do not exclude files
from OneDrive synchronization.
