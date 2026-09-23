# Power Apps connector definitions

`MILSTRIP-Local-Dev-API.swagger.json` is the unchanged connector export supplied
by the owner on 2026-09-23 after a successful gateway `GetHealth` test.

- Swagger/OpenAPI 2.0; HTTP host `127.0.0.1:8000`, base path `/api/v1`.
- One operation: `GetHealth` (`GET /health`).
- Declares Basic authentication; contains no credentials.
- The successful test used a temporary health-only endpoint. It does not prove
  backend authentication enforcement or availability of application routes.

This folder holds Power Apps importable connector definitions. The separate
`docs/operator-api.openapi.json` describes the backend API's runtime contract.
Gateway selection and saved connection credentials are configured in Power
Platform and are not included in this Swagger export.

Next implementation work: enforce local API authentication and extend the
connector with intake, results, review and history operations. The exported
`info.title` is still the wizard default; it can be corrected with that update.
