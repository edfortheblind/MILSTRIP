# Existing Power Apps connector

The generated `MILSTRIP-Local-Dev-API.swagger.json` extends the verified existing
connector to seven operations. Reuse MILSTRIP Local Dev API, the organization
Default environment, MILSTRIP solution and MILSTRIP-DEV-LAPTOP gateway.

Preserved path: HTTP `127.0.0.1:8000`, base `/api/v1`, Basic authentication.
Gateway selection and credential values are configured in the connection,
not the Swagger file. Keep the gateway checkbox selected after updating.

| Operation | Method and relative path |
| --- | --- |
| GetHealth | GET /health |
| CreateIntakeRequest | POST /intake/requests |
| ListIntakeRequests | GET /intake/requests |
| GetIntakeRequest | GET /intake/requests/{request_id} |
| ListRecordResults | GET /intake/requests/{request_id}/records |
| CreateReviewDecision | POST /records/{record_id}/review-decisions |
| ListAuditEvents | GET /intake/requests/{request_id}/audit-events |

Generate with `.venv/Scripts/python.exe scripts/export_powerapps_connector.py`;
add `--check` for drift detection. `docs/operator-api.openapi.json` remains the
OpenAPI 3.1 runtime reference. Nullable fields become `x-nullable`, references
become definitions and request bodies become Swagger body parameters. Only
validation-error location indices are represented as strings for diagnostics;
unsupported new unions fail generation. Domain schemas retain their types.

The full artifact is validated with openapi-spec-validator and compared with
runtime operation IDs, authentication and response schemas in tests.
[Microsoft requires OpenAPI 2.0](https://learn.microsoft.com/en-us/connectors/custom-connectors/define-openapi-definition).
Tenant import and authenticated gateway testing remain pending.

Follow the [continuation SOP](../../sop/local-api-development.md) to update the
existing connector and its private connection credential, then run gateway tests.
