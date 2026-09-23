# Local API authentication and connector increment

Date: 2026-09-23. Local implementation verified; connected acceptance blocked
on tenant/Studio application integration. No independent
Audit was performed. No commit/push occurred in this increment.

## Delivered locally

- Basic authentication across all seven API operations, authenticated intake
  and review audit identity, rejection of identity spoofing and loopback/database
  enforcement. No legacy write endpoint or migration was added.
- Private PBKDF2-SHA256 verifier setup with random salt, DACL-only directory
  protection and a repeatable loopback launcher with proxy trust disabled.
- Typed runtime responses and deterministic Swagger 2.0 generation extending
  the existing connector, preserving HTTP host/base path and GetHealth ID.
- Four canvas control sets for the owner's saved app ID
  `7f1b64d0-d51a-4ec8-84ad-2b18fe8c2f82`, with retry/conflict handling and
  canonical text preservation. These have not been applied in Studio.
- Updated SOPs, API contract, app-ID lookup steps and restart handoff.

## Evidence

`MILSTRIP_TEST_DATABASE_URL` used the approved local database with the existing
PostgreSQL authentication setup. The full suite passed **176 tests**, with the
same two Starlette/httpx/AnyIO deprecation warnings as the baseline. This includes
real persistence, transaction rollback, two-session review conflict, all-route
missing/invalid authentication, caller identity spoofing, malformed credentials,
database boundary checks, schema validation and Windows ACL retry regressions.

`scripts/check_local_api_http.py` started an isolated real Uvicorn process using
an ephemeral identity and made read-only HTTP calls: absent/invalid credentials
401, authenticated health and listing 200, missing request records 404. Health
confirmed database AVAILABLE. The process and ephemeral verifier were removed.
The existing gateway test process was not replaced by this smoke check.

Installed PostgreSQL parser parity passed **18 cases × 14 fields**. Runtime
OpenAPI and Swagger `--check` commands passed; openapi-spec-validator accepted
the generated Swagger definition. `git diff --check` passed.

The four canvas control sets passed instance-structure checks against Microsoft's
v3 schema retrieved from the PowerApps-Tooling repository, SHA256
`fc2816840271186d3b3057a1316bdb682bf6d95f4ae4849eab1fd47e2149ed13`.
That upstream schema contains an invalid regex in its unused CodeComponent
definition, so full meta-schema checking failed; Draft7 instance validation
was applied to these first-party controls only. This is not Power Fx execution
or connector-binding validation.

The owner reported a rejected short password, followed by SeSecurityPrivilege
errors on repeated Set-Acl. The fixed DACL-only permission step succeeded twice
on the actual private directory without elevation, and the automated regression
repeats the operation on a fresh temporary folder. Password retry and preservation
of an existing verifier after failed rotation are also covered by tests.

## Remaining acceptance

The owner subsequently confirmed private credential setup succeeded. The verifier
exists and its structure was checked without displaying credential values.
The identified health-only process (PID 31992) was stopped and the authenticated
launcher started in a hidden background PowerShell process (PID 30308).
The real API is listening on 127.0.0.1:8000 (Python PID 35068). Live checks
confirmed missing credentials return 401 for health and request listing, invalid
credentials return 401, and the runtime schema is version 0.3.0 with seven
operations. Valid owner credentials have not been tested by the agent because
the private password is intentionally unknown. These process IDs are a snapshot;
recheck listeners before restarting.
PAC was not on PATH or found in the checked Microsoft local application path;
no authenticated Power Platform tools were available. Gateway service
PBIEgwService was Running. The owner subsequently ran the private credential
check and supplied evidence of local HTTP 200. After creating/selecting a
replacement connection on the same connector and gateway, the owner supplied
a GetHealth HTTP 200 screenshot. This verifies authenticated gateway access
to the real API. Its response body was not visible, so database AVAILABLE is
not inferred from that screenshot. A subsequent owner screenshot confirms the
saved connector Test tab now displays Operations (7) and the selected working
connection. The import gate is complete.

The owner requested one standalone test and continuation of implementation.
`scripts/Test-LocalWorkflow.ps1` passed all seven real HTTP operations, health,
authentication failures, mixed valid/rejected intake, canonical spaces, actor
derivation, records/history pagination, exact retry, stale/changed-command
conflicts, invalid approval rejection and audit counts. Its uniquely tagged
synthetic rows were removed and cleanup verified. The test used an isolated
temporary API/identity; it does not claim Power Platform execution evidence.

Next, verify application calls during canvas integration, confirm saved-app solution membership and apply
the control sets in Studio. App checker, review retry/conflict behavior, paging,
gateway outage recovery and icon application require tenant readback.

Basic credentials identify the development connection, not each signed-in user.
Shared rollout needs per-user authorization. Canvas input and pending commands
are held in memory only; browser restart requires checking request/history before
repeating actions. Intake POST has no idempotency guarantee; its UI blocks blind
resubmission after an uncertain outcome. No production configuration, operational
legacy write, dual write, SQL retirement or shared-history change was performed.

## Superseding canvas execution evidence

The later session verified desktop automation, operated Studio directly and
validated the private stored credential locally without printing it. Existing
connection correction and live canvas workflow results supersede the earlier
"no automated tenant access" and "next, apply controls" observations above.
See [canvas implementation evidence](CANVAS_IMPLEMENTATION_2026-09-23.md).
