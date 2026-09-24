# MILSTRIP runtime configuration

**Status date:** September 24, 2026. **Audience:** administrator of the API host.

**MILSTRIP Stage** and **MILSTRIP Prod** are published in the existing solution
with separate connections. Stage has an identity in the existing local PostgreSQL database.
The Prod runtime profile is disabled with no database target selected.
App IDs and deployment settings are in the
[canvas deployment manifest](../powerapps/canvas/deployment-manifest.json).

Standalone player acceptance is blocked by the current account's Power Apps
licensing. IT owns resolution; no trial was started. Studio Preview checks do
not remove that requirement.

## What the environments control

Each app uses a different connection to the existing custom connector and
gateway. Its API credential selects a fixed server-side profile. Stage and Prod
must have separate databases and different API usernames/verifier files.
Operators do not choose a connection string or environment inside an intake.

Both apps share the same local API process and gateway. Restarting or deploying
that API affects both apps. Separate database profiles provide data isolation;
independent runtime releases require separate backend deployments.

The administrator screen is a Windows application on the API host. It is not a
Power Apps screen and does not send database credentials through the connector.
An operator-facing configuration screen may show health and environment, but
must not edit the destination.

## Open the administrator screen

From the repository's PowerShell terminal:

```powershell
.\scripts\Configure-Runtime.ps1
```

The launcher prepares access-restricted private storage and opens **MILSTRIP
database configuration**. The default configuration is `.cred/runtime.json`.
Both launchers use an explicit `-ConfigFile` path first, then
`MILSTRIP_RUNTIME_CONFIG_FILE`, then this repository default.
The provisioning command reads that variable or the default. Keep all three
tools on the same file. An alternate file must still be directly inside `.cred`.

Connection strings are stored in that private file. It is Git-ignored and
protected by Windows permissions, but is not encrypted by this application.
Keep copies in protected storage; exclude the file from shared documents,
screenshots and public artifacts. The screen displays only provider,
host/port and database for the saved target.

Both credential verifiers must exist before the API starts:

| Profile | Default verifier file | Binding |
|---|---|---|
| Stage | `.cred/api-credential.json` | Existing Stage API identity |
| Prod | `.cred/api-prod-credential.json` | Different Prod API identity |

When a verifier needs to be created or deliberately rotated, use
`Set-LocalApiCredential.ps1 -Environment stage` or `-Environment prod`; the
utility prompts privately and selects the corresponding file. Do not overwrite
the Stage verifier while preparing Prod. The connector connection must use the
matching API username and password, not the database login. A disabled Prod
profile still needs its verifier so the runtime configuration can load.

## Configure an existing, provisioned destination

1. Select **App environment**: `stage` or `prod`.
2. Select **Database provider**: `postgresql` or `sqlserver`. Set a short
   **Display label** identifying the environment.
3. Enter **Replacement connection string**. The field is masked. Leave it blank
   to retain the saved string; changing providers requires a replacement.
4. Select **Test connection**. A pass confirms access, application read probes
   and the matching environment/schema identity. It does not prove write
   permissions, concurrency behavior or production readiness.
5. Select **Enable this environment** when the target is ready. A changed or
   newly enabled destination must pass its test before saving.
6. Select **Save pending configuration**. The running API is unchanged. Save the
   current profile before selecting the other environment.
7. Follow the restart procedure below and verify each app's environment.

**Test connection** does not create tables, submit an intake or modify records.
Unknown database targets require provisioning first; repeatedly testing cannot
create the missing application schema.

## Prepare a new destination

Have the DBA create or approve the database and its runtime identity. Use a
runtime database login limited to the application's required operations; schema
provisioning may require a separate administrative account.

Save the new destination while **Enable this environment** is unchecked. This
allows its connection string to be stored privately without activating it.
Then use the dedicated `Initialize-ApplicationDatabase.ps1` /
`initialize_application_database.py` provisioning entry point. It selects the
saved `stage` or `prod` profile; no connection string belongs on its command line.

Preview the saved target first. This command does not connect to the database:

```powershell
.\scripts\Initialize-ApplicationDatabase.ps1 -Environment prod
```

After checking the printed target and the provisioning authority, copy its
complete `provider | host:port | database` value into the confirmation argument:

```powershell
.\scripts\Initialize-ApplicationDatabase.ps1 `
  -Environment prod `
  -ProvisionApplicationSchema `
  -ConfirmTarget '<exact target printed by preview>'
```

Use `-Environment stage` for a Stage target. The Python equivalents are
`--environment`, `--provision-application-schema` and `--confirm-target`.

This operation calls `provision_schema` to create five application data tables
and `environment_identity` (six tables total) in an existing database. Existing compatible tables
and data are preserved. A mismatched environment or schema needing migration
is an error, not permission to relabel or rebuild the database. It does not
create a database or touch operational shipment tables.

After provisioning, return to the configuration screen, test the destination,
enable it and save. Verify writes with an approved synthetic transaction before
releasing the app to operators. Do not use the recorded Azure SQL production
source for this step until its freeze and deployment authority are resolved.

## Connection string formats

These examples contain placeholders. Enter real values privately in the
administrator screen.

Remote PostgreSQL accepts a libpq URL or keyword string. It requires
`sslmode=verify-full` and a trusted certificate matching the hostname:

```text
host=pg-stage.example.invalid port=5432 dbname=milstrip_stage user=DB_USER password='PRIVATE_PASSWORD' sslmode=verify-full sslrootcert=C:/Certificates/root-ca.pem
```

Local PostgreSQL may use the existing loopback configuration. Service-file,
explicit passfile, host-address override and session-option parameters are not
supported by this configuration interface. Moving to an IT VM requires its
actual hostname, database, network access and certificate trust to be accepted.

The API rejects inherited `PGHOSTADDR`, `PGSERVICE`, `PGSERVICEFILE`, `PGOPTIONS`
and `PGPASSFILE` settings. Remove those overrides from the API process's launch
environment and use its private profile. This prevents libpq defaults from
redirecting the saved destination or applying undocumented session settings.

Azure SQL / SQL Server uses a raw ODBC connection string. Install Microsoft
ODBC Driver 17 or 18 for SQL Server on the API host:

```text
Driver={ODBC Driver 18 for SQL Server};Server=tcp:sql-stage.example.invalid,1433;Database=milstrip_stage;Uid=DB_USER;Pwd={PRIVATE_PASSWORD};Encrypt=yes;TrustServerCertificate=no;
```

Keep encryption and certificate verification enabled. Provider support in code
does not establish that a particular Azure SQL target has passed runtime tests.
Use the provider's quoting/escaping rules when credentials contain delimiters.

## Activate and verify

1. Arrange a pause for both apps. Let active requests finish and reconcile any
   unknown submission or review outcome before changing destinations.
2. Retain the previous private configuration in protected storage for recovery.
3. Stop the identified running MILSTRIP API process. Do not terminate an unknown
   process merely because it uses port 8000.
4. Start the API from the repository:

   ```powershell
   .\scripts\Start-LocalApi.ps1
   ```

5. Check `GetHealth` using each app's connection. Confirm the expected
   `environment`, `provider`, `target_label`, `configuration_revision`, and
   `ready=true`. A disabled environment reports `ready=false`; it cannot process
   intakes or reviews.
6. Open the matching app. Verify existing history and perform the approved
   acceptance check. Keep its Request ID and inspect the saved receipt, review
   and audit evidence.

If health reports the wrong environment or missing schema, stop and correct the
binding/target. Do not work around the failure by using the other app's
credentials. An unsuccessful connection does not cause an automatic fallback.

## Move data separately

Saving a new connection string changes where future requests run. It does not
copy existing intake text, records, decisions or history. A newly provisioned
empty database has no earlier requests.

For PostgreSQL-to-PostgreSQL moves, use an approved backup/restore procedure and
verify counts, IDs, canonical values, review versions, sequence values and audit
evidence. A PostgreSQL-to-SQL Server move requires an explicit provider import
and equivalent verification. Preserve the intended environment identity; a
restored Stage database remains Stage until an approved migration says otherwise.

After new writes occur at the destination, changing the string back to an old
database can lose new work or duplicate actions. Pause both writers and reconcile
the changes before returning. Configuration rollback alone is not data recovery.

The retained September 24 test request
`1d0c784d-c3bf-495c-928c-0b66687a58a4` must remain in Stage. Connection setup and
verification do not authorize deleting it.

## Troubleshooting

| Result | Administrator action |
|---|---|
| Configuration cannot load | Check file format, both verifier files and distinct usernames; use the native screen to save a valid revision. |
| Another editor changed configuration | Close and reopen the screen before editing. The stale snapshot was not saved. |
| Connection test fails | Check target, login, TLS trust and the six application tables, including environment_identity. Raw connection strings are not diagnostic output. |
| Target is marked for the other environment | Correct the destination. Do not overwrite its marker to bypass isolation. |
| Saved target has not changed in the app | Restart the shared API and compare the reported configuration revision. |
| Player asks for a Power Apps plan or trial | Refer the account to IT for the approved license. The owner chose not to start a trial. Publication and a passing Preview do not resolve licensing. |
| App is published but unavailable | Check API host, gateway, database and connection availability after licensing is resolved. Publication does not replace those services. |

Design and source: [ADR 0005](adr/0005-runtime-profiles.md),
[configuration screen](../scripts/configure_runtime.py),
[profile validation](../api/profiles.py), and
[transaction/provisioning implementation](../api/persistence/repository.py).
