# MILSTRIP Power Apps laptop DEV handoff

Copy to `local-discovery/powerapps-dev-handoff.md` and fill in nonsecret values.
Do not include passwords, access tokens, client secrets or gateway recovery keys.

## Platform

- Work account UPN:
- Tenant ID:
- Cloud: Public / UsGov / UsGovHigh / UsGovDod / China
- Environment display name:
- Environment ID:
- Environment URL (Dataverse organization URL):
- Environment type: Developer
- Region:
- Dataverse ready: yes / no
- Developer entitlement confirmed: yes / no
- Environment roles/customization permissions:
- Custom connector/gateway policy allowed: yes / pending
- Administrator blockers, if any:

## Solution and app

- Solution display name:
- Solution unique name: MILSTRIP
- Publisher unique name:
- Publisher prefix: tab
- Existing canvas app name/ID: none / value
- Existing connector name/ID: none / value
- Existing connection reference: none / value

## Laptop gateway and API

- Gateway name:
- Gateway cluster/ID (if visible):
- Standard mode: yes / no
- Gateway machine name:
- Same laptop as API/PostgreSQL: yes / no
- Gateway region:
- Gateway online and accessible to my account: yes / no
- Recovery key saved privately: yes / no (never include the key)
- API origin: http://127.0.0.1:8000
- API health: OK / DEGRADED / not tested
- API currently running: yes / no
- Database: localhost:5432 / trav3pl-psqldb-stage
- Existing database authentication available to local process: yes / no
- Local HTTPS required by policy: yes / no / unknown
- Other routing/proxy restrictions:

## Identity and CLI

- Proposed dedicated API development username: milstrip-dev-ed
- API Basic authentication: awaiting implementation; no work password supplied
- PAC executable path:
- PAC version:
- PAC profile name: MILSTRIP-DEV
- `pac auth who` confirmed correct environment/account: yes / no
- `pac solution list` shows MILSTRIP: yes / no
- Same Windows user as the coding workspace: yes / no
- Existing browser/app ownership or access constraints:

## Handoff scope

Continue implementation using the named DEV environment and MILSTRIP solution:
local authentication, connector artifacts, solution components, synthetic tests
and a development canvas app. Keep the API and PostgreSQL on this laptop.
Any outstanding tenant policy, MFA or Studio-only action is listed below.

- Outstanding actions:
- Date prepared:
