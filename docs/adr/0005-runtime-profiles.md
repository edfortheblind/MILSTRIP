# ADR 0005 — Fixed Stage and Prod database profiles

**Date:** September 24, 2026

**Status:** Implemented in API 0.4.0; apps published; Prod target and player acceptance pending

## Context

The owner approved using the existing development app as **MILSTRIP Stage** and
creating **MILSTRIP Prod** in the existing solution. Both must support a future
PostgreSQL or Azure SQL destination without exposing connection strings to
operators. The existing connector and gateway remain in use.

The original API combined PostgreSQL queries with a hard-coded local database
restriction. Changing a connection string alone could not support SQL Server.
One global destination also could not serve two isolated app environments.

Stage is published and uses the existing local PostgreSQL database with a
provisioned Stage identity. The separate Prod app is published with its connection
verified. Both apps belong to the existing solution. The Prod runtime profile is disabled and
has no selected database target. Neither
the planned IT VM nor the recorded Azure SQL production database is an accepted
new runtime destination. App IDs and per-app source settings are recorded in
the [deployment manifest](../../powerapps/canvas/deployment-manifest.json).
The current account requires a Power Apps plan for standalone player acceptance;
the owner assigned licensing to IT and did not start a trial.

## Decision

Use one API process with an immutable startup configuration containing exactly
two profiles: `stage` and `prod`. Each profile has a provider, display label,
connection string and enabled state. Each has a different API credential file
and username. Authentication binds a request to one profile; the operator
cannot supply a database or override that binding.

Retain the existing connector and gateway. Give each app its own connection to
that connector, using the corresponding credential. Reuse the existing app ID
for Stage and give Prod a separate app ID. The health response reports the
authenticated environment, provider, display label, configuration revision and
readiness. Apps must check their expected environment before enabling work.

An application-owned `milstrip_app.environment_identity` table stores the
database's `stage` or `prod` identity and schema version. Runtime operations
verify this marker. Normalized connection targets catch common duplicate
destinations; the database marker also rejects a Stage database reached through
a different DNS name by a Prod profile. Missing or mismatched identity fails
closed. Runtime never creates or relabels the marker.

Replace provider-specific route SQL with one SQLAlchemy Core repository.
`postgresql` uses psycopg; `sqlserver` uses pyodbc and a supported Microsoft ODBC
driver. The six application tables share a model with explicit provider handling
for locks, canonical length, JSON, timestamps and nullable unique indexes.
Existing PostgreSQL tables and records remain in place.

The repository transaction boundary is:

```python
with open_repository(profile.provider, profile.connection_string) as repository:
    repository.validate_identity(profile.profile_id)
    result = repository.create_intake(...)  # or another application operation
# A successful write response is returned after commit.
```

HTTP authentication and cursor encoding stay in the API layer. The repository
returns `Page(items, has_more)` and `ReviewResult(decision, replayed)` for reads
and review commands. Existing operation IDs and receipt/review semantics remain
unchanged. The parser remains independent of the database provider.

## Configuration and provisioning

The administrator uses a native Tkinter screen on the API host. It shows a
sanitized destination and accepts a masked replacement connection string. It
never displays a saved string. Operators do not receive this capability through
the canvas app or custom connector.

Configuration lives in the Git-ignored, Windows-ACL-restricted `.cred`
directory. Connection strings are stored there; the current implementation does
not encrypt that file. Treat its copies and backups as credentials. API password
verifiers are stored in separate files.

**Test connection** performs read checks. **Save pending configuration** writes
an atomic, revision-checked snapshot. Restarting the API activates it; a running
request keeps its original destination. Both credential verifiers are required
even while Prod is disabled.

Schema provisioning is a separate administrator operation. It creates only
application metadata and its identity in an existing, approved database. It
does not create a database, alter operational `dbo` tables, move history or
convert an incompatible existing schema. Runtime startup and health checks
never provision tables. See [the administrator SOP](../RUNTIME_CONFIGURATION.md).

## Consequences and limits

- Stage and Prod data are separated by database and authenticated profile. They
  still share API code, process, laptop and gateway availability. A backend
  release or restart affects both. Fully independent deployment requires
  separate API deployments and corresponding connection routing.
- The shared Basic connection identifies the API account in audit records.
  Publishing an app does not add individual-user API authorization.
- Remote PostgreSQL requires verified TLS. SQL Server requires encrypted
  transport with certificate validation. No automatic destination fallback or
  dual write is introduced.
- Changing a connection string does not migrate data. An empty destination
  starts with empty history; migration and reconciliation remain separate work.
- SQL Server dialect support is implemented separately from live Azure SQL
  acceptance. The recorded SQL freeze still requires resolution before any
  production provisioning or write.
- This decision supersedes ADR 0004's single hard-coded database target with
  validated profiles. Its local API/gateway boundary remains. ADR 0003's
  unresolved delivery contract is unchanged; this work adds no legacy handoff.

Implementation references: [profiles](../../api/profiles.py),
[runtime binding](../../api/runtime.py), [authentication](../../api/auth.py),
[repository](../../api/persistence/repository.py), and
[schema](../../api/persistence/schema.py).
