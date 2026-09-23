# Standalone local workflow test

Run one command from the repository terminal:

```powershell
.\scripts\Test-LocalWorkflow.ps1
```

No password entry or individual Swagger tests are needed. The command starts a
temporary loopback API on an available port, uses a generated temporary identity
under `.cred`, and exercises the installed local database. The existing API on
port 8000 and its gateway connection remain running.

The workflow verifies:

- Missing/invalid credentials return 401; authenticated health returns AVAILABLE.
- All seven operations respond through real HTTP.
- Synthetic intake returns one valid and one rejected record with issues.
- Request details and intake/review audit actors derive from authentication.
- Canonical text retains all 80 characters, including trailing spaces.
- Record and history pagination preserve scope/order.
- Review returns 201, exact retry returns 200 without duplicate writes, and
  stale versions/changed retry content return 409.
- Approval of rejected input is refused; review does not rewrite validation.
- Scoped audit history contains exactly one intake and one review event.

The test commits only synthetic `milstrip_app` metadata marked with a unique
run UUID. It stops the temporary server, removes that run's rows, verifies
cleanup and deletes its temporary verifier. Application identity sequences may
advance; operational legacy tables are never written. The database target is
restricted to the approved localhost database and port. Required migrations must
already be installed; this command applies no DDL.

On 2026-09-23 the command passed, including cleanup. The owner supplied a screenshot
showing the saved connector's **Operations (7)** and its selected connection.
Authenticated gateway GetHealth 200 was confirmed previously. This standalone
test validates the local API/database workflow, not Power Platform's connector
serialization or Power Fx. Those integration checks will be performed while
implementing the existing canvas app, without repeating individual Swagger tests.

## Continue implementation

Open saved app `7f1b64d0-d51a-4ec8-84ad-2b18fe8c2f82` in Studio, add the existing
MILSTRIP Local Dev API connection through Data, then apply the prepared control
sets from `powerapps/canvas`. Confirm the actual data-source identifier before
pasting formulas. Preserve existing app work and reuse its solution membership;
do not create another app or connection if the working connection is available.
