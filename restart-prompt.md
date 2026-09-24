# New-session prompt

## Current continuation - September 24, 2026

Read `AGENTS.md`, `docs/master.md` and `OWNER_PROFILE.md`, then inspect Git status
before changing files. The working tree contains the current runtime/profile and
documentation increment. Do not restart the earlier authentication or canvas
implementation work from historical prompts.

Read these current references:

- `docs/RUNTIME_CONFIGURATION.md` and `docs/adr/0005-runtime-profiles.md`.
- `powerapps/canvas/README.md` and `deployment-manifest.json`.
- `powerapps/connectors/README.md` and the generated Swagger definition.
- `sop/powerapps-setup.md` for tenant maintenance and publication.
- `docs/delivery/RETAINED_RUNTIME_TEST_2026-09-24.md` for retained test evidence.

## Implemented state

- **MILSTRIP Stage** is published; app ID
  `7f1b64d0-d51a-4ec8-84ad-2b18fe8c2f82`. This is the original development app.
- **MILSTRIP Prod** is published; app ID
  `0aa02d8b-c7fa-42cc-87e8-6d287bd4c897`. Its database profile is disabled because
  no independent Prod target has been selected.
- The standalone Prod player requested a Power Apps plan for the current
  account. The owner assigned licensing to IT; do not start a trial. Studio
  Preview acceptance is recorded, but standalone player acceptance remains
  blocked until IT resolves licensing.
- The existing organization Default environment and MILSTRIP solution contain
  both apps and the existing MILSTRIP Local Dev API connector. The existing
  MILSTRIP-DEV-LAPTOP gateway is reused. Do not create another solution,
  environment, connector or gateway to repeat this setup.
- Each app has a fixed named formula in **App.Formulas**:
  `AppEnvironment = "stage";` or `AppEnvironment = "prod";`. Use the matching
  source variant from the deployment manifest. The shared environment check runs
  in **OnVisible on all four screens** and through **Check connection**.
  Mismatched or unavailable environments block operations. Do not replace this
  constant with an operator-selectable variable.
- API **0.4.0** runs on `127.0.0.1:8000`, base `/api/v1`. Its seven operation IDs
  remain stable. Basic credentials map server-side to fixed profiles; health
  returns environment, provider, label, revision and readiness. Audit actor is
  the API account, not the individual Power Apps user.
- Stage uses `localhost:5432/trav3pl-psqldb-stage`, schema `milstrip_app`, with
  `environment_identity` marked `stage`. The repository uses SQLAlchemy Core
  with psycopg or pyodbc. SQL Server support has compilation/contract evidence;
  no live Azure SQL acceptance is claimed.
- Native `scripts/Configure-Runtime.ps1` manages private connection strings.
  Test is read-only; saving takes effect after API restart. Explicit provisioning
  uses `scripts/Initialize-ApplicationDatabase.ps1`; it is never automatic on
  startup or a health check. Both credential verifiers are required even with
  Prod disabled. All sensitive configuration remains inside restricted `.cred/`.
- Separate profiles isolate data, but both apps share one backend process and
  release. API restarts and connector/backend changes can affect both.
- The final suite passed 242 tests in 91.34 seconds with two dependency warnings.
  The API restarted during that suite. After restart, a fresh Stage Studio
  Preview showed Ready and loaded recent
  requests and results. See `docs/delivery/RUNTIME_PROFILES_2026-09-24.md`; this
  does not establish licensed standalone player acceptance.
- Published Stage and Prod `.msapp` backups are retained under
  `%LOCALAPPDATA%\MILSTRIP\backups\`. The delivery evidence records their filenames
  and SHA-256 hashes. Exported source confirms the fixed environment formulas,
  four guarded screens and distinct connection references.

## Retain these records

Do not delete the owner's September 24 runtime request
`1d0c784d-c3bf-495c-928c-0b66687a58a4` or its related rows. It contains two records,
two saved reviews and three audit events. The read-only result query is
`db/queries/retained_runtime_2026-09-24.sql`.

The Stage publication check is also retained:
`ff3f3cb5-04f5-4135-af74-f8db41962673`. Do not include either request in automated
synthetic cleanup. New tests need their own identifiers and retention policy.
Its read-only query is `db/queries/retained_stage_publication_2026-09-24.sql`.

## Remaining work and boundaries

1. Resolve the actual Prod target with the owner: an independently provisioned
   local database, an approved supplied target, or continued disabled status.
   Never point Prod at Stage to make its health check pass.
2. Resume standalone player acceptance after IT resolves licensing. Check the
   latest delivery evidence before repeating tests or publication; both apps
   already have published versions.
3. Keep connection changes separate from data migration. New destinations need
   explicit provisioning and acceptance; history is not moved by a new string.
4. Preserve canonical 80-character values, receipt semantics, review command
   idempotency, version conflicts and environment isolation when extending code.
5. Accept the forthcoming change document through `inbox/README.md`. New incoming
   files are ignored by Git; the README and existing tracked reference files
   remain versioned. Their arrival does not activate a change.

The existing Azure SQL production source remains subject to its recorded freeze
and authorization questions. The IT VM destination is not yet supplied. No legacy
shipment writer, stored-procedure execution, CSV export, FTP delivery or Boomi
receipt is connected. App publication and review approval do not enable those
operations.

Use available authenticated tools for tenant work; verify current access instead
of assuming earlier sessions survive. Keep credentials out of chat and artifacts.
Follow current owner instructions for shared-history writes; do not infer new
commit/push authority from an old continuation block. Report actual validation
and distinguish documentation review from a production Audit.
