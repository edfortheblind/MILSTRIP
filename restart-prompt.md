# New-session prompt

## Current continuation (2026-09-23)

The instructions below initiated a local authentication/connector increment.
Before resuming, inspect the uncommitted changes and read
`sop/local-api-development.md`, `docs/master.md` and `powerapps/canvas/README.md`.
App ID supplied by owner: `7f1b64d0-d51a-4ec8-84ad-2b18fe8c2f82`; reuse it.
Basic authentication and seven Swagger operations are implemented locally;
the old MILSTRIP_LOCAL_REVIEWER setting is obsolete. Password-validation and ACL
retry problems were fixed; the owner confirmed private setup succeeded. The real
authenticated API now runs on loopback port 8000 and missing/invalid credentials
return 401. The owner confirmed local credential HTTP 200 and supplied a gateway
GetHealth HTTP 200 screenshot after replacing the saved connection. The owner
then saved the expanded connector and supplied a Test screenshot showing all
seven operations. `scripts/Test-LocalWorkflow.ps1` passed the full local HTTP
workflow and synthetic cleanup. Continue canvas implementation; the owner prefers
the standalone test to repeated individual Swagger tests. Power Platform
application-operation acceptance is deferred to canvas integration.
The agent applied the four canvas control sets to the existing app using Windows
desktop automation and saved the unpublished draft. Live synthetic canvas intake,
results, review and history passed. Read docs/delivery/CANVAS_IMPLEMENTATION_2026-09-23.md
for evidence and remaining acceptance. New commit/push is not yet approved.

Credential storage now uses the Git-ignored, access-restricted root `.cred/`
folder. The owner-supplied credential text and API verifier were moved there;
launcher/runtime paths were updated and the API restarted. Passwords are unchanged.

## Original implementation request

Copy the block below into a new coding session opened in this MILSTRIP repository.

```text
Continue MILSTRIP implementation from the completed laptop-to-Power-Apps gateway setup.

First read AGENTS.md, docs/master.md and OWNER_PROFILE.md. Then read:
- sop/powerapps-setup.md
- sop/conversation-record.md
- docs/OPERATOR_API_CONTRACT.md
- docs/delivery/IMPLEMENTATION_PLAN.md
- powerapps/connectors/README.md and MILSTRIP-Local-Dev-API.swagger.json

Current state:
- Backend/operator API baseline is commit ae48b63 on main; later documentation
  adds the sop folder. Inspect Git status/history before changing anything.
- All 139 tests passed with the approved local database enabled. The backend
  OpenAPI artifact matched runtime. Two dependency deprecation warnings remain.
- PostgreSQL is on this laptop: localhost:5432/trav3pl-psqldb-stage.
  Application data uses milstrip_app; migrations 001-005 were applied locally.
- Power Apps uses the organization's EXISTING Default environment. MILSTRIP
  solution, TAB publisher and MILSTRIP Local Dev API connector already exist.
- Standard gateway MILSTRIP-DEV-LAPTOP is registered in Central US.
- Connector uses HTTP, host 127.0.0.1:8000, base /api/v1, Basic authentication,
  and GetHealth. The owner verified HTTP 200 through the gateway.
- Only a TEMPORARY HEALTH-ONLY process was started for that test. It does not
  validate credentials or expose application routes. Check its current process
  and listener state; do not assume it survived the previous session.
- Connector export: powerapps/connectors/MILSTRIP-Local-Dev-API.swagger.json
  (OpenAPI 2.0). Backend docs/operator-api.openapi.json is OpenAPI 3.1.
- Original app icon: assets/milstrip-app.png. A blank canvas app was opened;
  its final saved name/ID and solution membership still need verification.
- PAC/automated tenant access is not yet verified. Do not claim you can operate
  Studio or bypass MFA without checking available tooling.

Proceed with the next implementation increment:
1. Implement dedicated local development API authentication. Protect application
   routes, derive the reviewer from the authenticated identity, preserve the
   localhost/database boundaries, and test missing, invalid and valid credentials.
   The existing MILSTRIP_LOCAL_REVIEWER setting is not authentication.
2. Provide a private local credential setup and a repeatable laptop API launcher.
   Never print/store secrets in Git or ask me to paste a password/token in chat.
   Do not assume the existing connection's credentials are known or correct.
3. Extend the existing connector with intake creation, request listing/details,
   record results, versioned/idempotent review decisions and audit history.
   Preserve the verified gateway access path and produce importable OpenAPI 2.0.
4. Verify local behavior and schema consistency, then test via the existing gateway
   using available authenticated tools or concise owner-assisted UI steps.
5. Continue the canvas intake/results/review/history screens with the supplied icon.
   Verify what is already saved before creating another app. Handle conflicts,
   retries and errors without losing input or canonical trailing spaces.

Reuse the environment, solution, connector and gateway. Do not repeat initial
setup or create a separate Developer environment. Keep API/PostgreSQL on this
laptop; cloud deployment is later and still needs an API host.

SQL Server remains authoritative. No legacy operational writes, production
configuration changes, dual writes or retirement are authorized. Approval of a
review does not authorize delivery. The previously approved synthetic temporary-
table handoff test remains allowed within its documented bounds.

Make routine local implementation decisions and run appropriate checks without
asking me to approve the same scope again. Commit/push approval in the previous
session covered its delivered increments; follow AGENTS.md for new shared-history
writes. Ask only for genuinely missing business decisions, credentials entered
privately, unavailable permissions or UI-only steps.

Keep progress updates short and labeled. Report evidence, remaining limitations
and the next concrete step; do not call self-review an independent Audit.
```
