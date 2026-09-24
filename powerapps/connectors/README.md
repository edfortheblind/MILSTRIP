# Existing MILSTRIP custom connector

**Current contract:** API **0.4.0**, seven operations. Reuse MILSTRIP Local Dev API,
the existing organization Default environment, MILSTRIP solution and
MILSTRIP-DEV-LAPTOP gateway. The solution contains this connector and the published
MILSTRIP Stage and MILSTRIP Prod apps.

The current account's standalone player is blocked by Power Apps licensing.
IT owns resolution; no trial was started. Publishing the apps and verifying
their connections in Studio Preview do not complete player acceptance.

The connection route remains HTTP `127.0.0.1:8000`, base `/api/v1`, Basic
authentication through the selected gateway. Gateway selection and credentials
belong to each connection, not the Swagger artifact.
The existing connector's saved Basic authentication field labels are
**Username** and **Password**. Enter the dedicated API credential for that
connection; the labels do not identify or select its runtime environment.

## Separate connections, one connector

Stage and Prod use separate connections with different API usernames and
passwords. The API validates each credential and selects its fixed profile from
private configuration. A client field or header cannot choose a database.

Check the connection actually attached to each app. Similar display names do
not prove the binding. `GetHealth.environment` must match that app's fixed
`AppEnvironment` formula. Stage is currently ready on local PostgreSQL; Prod
is published but its runtime profile remains disabled without a target.

| Health field | Meaning |
|---|---|
| `environment` | Server-selected `stage` or `prod` |
| `provider` | `postgresql` or `sqlserver` |
| `target_label` | Administrator's safe display label |
| `configuration_revision` | Snapshot loaded when the API started |
| `ready` | Connection, application read probes and environment identity passed |
| `status`, `database`, `detail` | Availability and controlled diagnostic result |

A `200` health response alone is insufficient: a disabled or unavailable profile
returns `ready=false`. App operations require the correct environment and
readiness. Database strings never enter the connector or canvas formulas.

## Operations

| Operation | Method and relative path |
|---|---|
| GetHealth | GET /health |
| CreateIntakeRequest | POST /intake/requests |
| ListIntakeRequests | GET /intake/requests |
| GetIntakeRequest | GET /intake/requests/{request_id} |
| ListRecordResults | GET /intake/requests/{request_id}/records |
| CreateReviewDecision | POST /records/{record_id}/review-decisions |
| ListAuditEvents | GET /intake/requests/{request_id}/audit-events |

Generate the existing connector artifact:

```powershell
.\.venv\Scripts\python.exe scripts\export_powerapps_connector.py
.\.venv\Scripts\python.exe scripts\export_powerapps_connector.py --check
```

`MILSTRIP-Local-Dev-API.swagger.json` is OpenAPI 2.0; the backend reference
`docs/operator-api.openapi.json` is OpenAPI 3.1. Nullable fields become
`x-nullable`, references become definitions, and request bodies become Swagger
body parameters. Unsupported unions fail generation; validation-error location
indices are the single diagnostic conversion to strings.

The artifact is checked against runtime operation IDs, authentication and
response schemas. [Microsoft requires OpenAPI 2.0](https://learn.microsoft.com/en-us/connectors/custom-connectors/define-openapi-definition).
After an API contract change, update this existing connector, retain the gateway
setting, refresh the app's data source and verify both connections. A shared
connector change can affect both published apps.

The API audit uses the connection account. Publication does not add individual
reviewer authorization or automatically establish another user's connection
permissions. Follow the [tenant SOP](../../sop/powerapps-setup.md) for sharing and
connection verification, and the [administrator SOP](../../docs/RUNTIME_CONFIGURATION.md)
for private database configuration. Live Azure SQL acceptance remains pending.
