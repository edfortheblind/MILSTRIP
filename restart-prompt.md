# New-session prompt

## Current continuation - September 24, 2026

Read `AGENTS.md`, `docs/master.md` and `OWNER_PROFILE.md`, then inspect Git status
before changing files. The working tree contains the verified-user administration
increment. Reuse the backend, generated flows and six-screen Canvas source; do
not rebuild the earlier authentication or runtime-profile work.

Read these current references:

- `docs/TAB_SSO_SETUP_SOP.md` for the working management connection procedure and
  sysadmin recovery handoff.
- `docs/RUNTIME_CONFIGURATION.md`, `docs/adr/0005-runtime-profiles.md` and
  `docs/adr/0006-user-identity-and-administration.md`.
- `docs/delivery/IDENTITY_ADMIN_IMPLEMENTATION_CONTRACT_2026-09-24.md` and
  `docs/delivery/IDENTITY_ADMIN_STATUS_2026-09-24.md`.
- `powerapps/flows/README.md` and the generated broker sources.
- `powerapps/canvas/README.md`, `deployment-manifest.json` and the six-screen
  variants under `powerapps/canvas/broker/`.
- `powerapps/connectors/README.md` and the generated Swagger.
- `sop/powerapps-setup.md` for tenant maintenance and publication.
- `docs/delivery/RETAINED_RUNTIME_TEST_2026-09-24.md` for retained test evidence.

## Verified native state

- **MILSTRIP Stage** is published on the original app ID
  `7f1b64d0-d51a-4ec8-84ad-2b18fe8c2f82`. Licensing is resolved for the verified
  session. Its actual published player passed health and retained-results reads.
- **MILSTRIP Prod** is published as
  `0aa02d8b-c7fa-42cc-87e8-6d287bd4c897`. Its licensed player opens and reports
  `Database: DISABLED`. No independent Prod target is approved/configured.
- The existing organization Default environment and MILSTRIP solution contain
  both apps and the existing MILSTRIP Local Dev API connector. The existing
  MILSTRIP-DEV-LAPTOP gateway is reused. Do not create another solution,
  environment, connector or gateway to repeat this setup. The connector now has
  eight operations, including `InvokeBroker`; gateway connectivity is verified.
- Both broker references are bound and the latest paced definitions are imported.
  Stage `04d6229f-5ab8-f111-aaac-7ced8d6f317c` and Prod
  `fbe87a93-68ef-4efb-88db-facc21c125f6` are both **Started**. Resume these resources
  rather than import duplicates. Do not treat flow activation as native acceptance.
- The Power Automate Management connection **MILSTRIPManagementSSO**, ID
  `07c12ec437fa43e289082155a221a981`, is **Connected**. Power Automate's Connections
  page completed existing TAB SSO after the Power Apps designer attempts failed.
  OAuth and player licensing are resolved.
- Native readback confirms Claude and Mike have CanView grants on both apps and
  run-only grants on both flows. Their protected OWNER memberships are ACTIVE.
  Ed is ACTIVE ADMIN and retains platform deployment ownership. Kristen, Thomas
  and Shawn remain PENDING. Three executions of Kristen's command returned
  incomplete app readback. A final built-in pagination trial stalled on the first
  Makers GET for over eight minutes and was canceled around 23:48 UTC. Its
  durable execution/lease remains RUNNING; no Management permit is held. No
  permission mutation or Management call occurred in that final attempt. Earlier
  flow run-only grants remain verified; neither app CanView grant was added.
  Stop native attempts; no OAuth or IT policy change is requested.
- Both six-screen v2 drafts are saved and natively exported, with no direct API data
  source. Each executable export matches six screens, 81 controls and 679 source
  properties. App Checker reported zero formula errors and two literal-predicate
  warnings. Neither new version is published.
- Stage native checks passed for `GetCurrentUser`, `GetHealth`, `ListUsers`,
  `GetRuntimeProfiles`, Save draft and Test draft against the unchanged target.
  Prod SSO and administration/configuration reads passed with its database
  disabled. Apply, sharing/recovery and second-user acceptance remain pending.
- Two successful Stage run-metadata checks verified secure inputs/outputs without
  opening protected content; exact evidence is in `docs/TAB_SSO_SETUP_SOP.md`.
- Private control state has three active and three pending memberships; security
  enforcement and runtime authority remain inactive. The published four-screen
  apps still use the shared connection's API identity.

## Implemented source and validation

- The full source suite passed **372 tests; 73 database opt-in tests were skipped**,
  with two upstream dependency warnings in 77.51 seconds. The prior pagination/flow/package/sharing
  batch passed **43 tests**. This does not replace native tenant or
  live database acceptance. The earlier 242-test runtime increment
  is historical evidence; its licensing limitation has been superseded.
- The flow obtains the invoker through an invoker-owned Office 365 Users
  connection. The API derives tenant/profile from its private broker credential
  and evaluates directory object IDs. Client-supplied email, role or actor never
  authorizes access. TAB's existing managed Entra SSO remains the identity provider.
- Claude Furry and Mike Thompson are permanent in-app Owners. Ed, Kristen,
  Thomas and Shawn are Admins. All six directory identities were verified as
  enabled internal Members. Preserve their verified IDs and existing platform
  ownership; an app role does not grant maker/edit rights.
- Runtime drafts, read-only tests, actor-bound expiring receipts, revision checks,
  per-profile request draining and a single-worker process lock are implemented.
  Stage and Prod cannot share a database target. An enabled environment must be
  disabled before its target changes. A connection string does not move history.
- Membership changes use a durable lease per person across both broker flows.
  Removal denies API access immediately. Unknown platform writes retain the
  lease until the original execution is confirmed finished. Retry the same command.
- The Management connector allows five calls per minute per connection. A shared
  durable permit now surrounds each management read/write, followed by a 13-second
  cooldown. Flows wait on the server timestamp; API threads do not sleep. Unknown
  outcomes hold the permit across restarts. A busy reservation issues no call.
  Six native serial calls observed post-completion intervals of at least 13.516
  seconds. Concurrent calls and timeout recovery still require native acceptance.
- Six-screen Canvas variants add Configuration and Users. Error gates stop later
  actions after a failed broker result; saved drafts lock their fields; confirmed
  changes remain distinct from follow-up refresh failures. Native draft compilation
  and executable-source comparison passed; failure-path acceptance is incomplete.
- Stage uses `localhost:5432/trav3pl-psqldb-stage`, schema `milstrip_app`, with
  `environment_identity` marked `stage`. The repository uses SQLAlchemy Core
  with psycopg or pyodbc. SQL Server support has compilation/contract evidence;
  no live Azure SQL acceptance is claimed.
- Before cutover, `.cred/runtime.json` remains the running configuration source.
  After explicit cutover, `.cred/control.json` becomes the authority; startup no
  longer needs legacy runtime/verifier files, and the legacy configuration editor
  refuses changes. `Start-LocalApi.ps1` uses one worker and validates the selected
  authority; `-ValidateOnly` performs preflight without starting a server.
  First activation rejects an import that differs from the current legacy
  revision/content; back up and review stale imports without overwriting drafts.
- Explicit provisioning uses `scripts/Initialize-ApplicationDatabase.ps1`; startup
  and health checks never create schema. All sensitive configuration remains in
  restricted `.cred/`. The in-app administration store is independent of both
  business databases and remains available with Prod disabled.
- Separate profiles isolate data, but both apps share one backend process and
  release. API restarts and connector/backend changes can affect both.
- Published Stage and Prod `.msapp` backups are retained under
  `%LOCALAPPDATA%\MILSTRIP\backups\`. The delivery evidence records their filenames
  and SHA-256 hashes. Exported source confirms the fixed environment formulas,
  four guarded published screens and distinct connection references. Separate
  `MILSTRIP-{Stage,Prod}-20260924-admin-draft-v2.msapp` exports preserve the latest
  six-screen drafts and four verified role-display/message-handling fixes. See
  `docs/delivery/CANVAS_SOURCE_ASSEMBLY_2026-09-24.md` for hashes and comparison.
  Do not confuse a saved draft with the published release.

## Retain these records

Do not delete the owner's September 24 runtime request
`1d0c784d-c3bf-495c-928c-0b66687a58a4` or its related rows. It contains two records,
two saved reviews and three audit events. The read-only result query is
`db/queries/retained_runtime_2026-09-24.sql`.

The Stage publication check is also retained:
`ff3f3cb5-04f5-4135-af74-f8db41962673`. Do not include either request in automated
synthetic cleanup. New tests need their own identifiers and retention policy.
Its read-only query is `db/queries/retained_stage_publication_2026-09-24.sql`.

## Next work and boundaries

1. Stop native sharing retries. Obtain independent design/review for canceled-run
   reconciliation and finite permission readback. Preserve Kristen's command
   `689cf9a0-cfe5-4fc7-9496-bb1e2db0c32c`, plan
   `b68690a1-837a-44ce-9950-248e4eb52df4`, execution
   `fe7ea517-271b-4393-bfd0-f51657b9f99e` and RUNNING lease
   `6ddd23d7-e3b6-458e-adfa-967bf5d91c81`. Do not clear the lease, fabricate a
   callback, reset the plan, create a replacement command or undo partial grants.
   Native run `08584113137259107903122568693CU13` began at
   `2026-09-24T23:39:19.5961106Z`; native UI cancellation was confirmed around
   23:48 UTC, but durable reconciliation has not occurred. Read
   `docs/delivery/MAKERS_PERMISSION_PAGINATION_2026-09-24.md` before any recovery.
   Both broker flows and OAuth connections work; this is a developer blocker.
   Advisory independent review accepts this handoff as fail-closed; this is not
   a formal Full-profile Audit. Any future host
   recovery must verify terminal native cancellation, that every grant mutation
   never started, exact plan/revision/lease/execution ownership and no active
   Management call. It may close only the aborted execution; membership must
   remain pending. This recovery is not implemented or authorized for execution
   by these instructions.
2. Complete draft Apply and recovery checks, disabled-Prod administration,
   Operator restrictions, protected-owner rejection, wrong-profile rejection and
   second-user identity/audit acceptance. Preserve any draft/test command needed
   for retry. Review the exported accessibility findings before publication.
3. Complete controlled security cutover under ADR 0006. Publish only accepted
   versions; check their actual players and verify that legacy shared credentials
   cannot bypass authorization. Keep the previous release backups.
4. Resolve the independent Prod target with the owner. Never point Prod at Stage
   to pass health checks. New destinations need explicit provisioning and acceptance;
   connection changes and data migration remain separate.
5. Preserve canonical 80-character values, receipt semantics, review command
   idempotency, version conflicts and environment isolation.
6. Accept the forthcoming change document through `inbox/README.md`. New incoming
   files are ignored by Git; the README and existing tracked reference files
   remain versioned. Their arrival does not activate a change.

The existing Azure SQL production source remains subject to its recorded freeze
and authorization questions. The IT VM destination is not yet supplied. No legacy
shipment writer, stored-procedure execution, CSV export, FTP delivery or Boomi
receipt is connected. App publication and review approval do not enable those
operations.

Public visual guide **1.4.0** is published from `edfortheblind/milstrip-guide`
commit `af9334de8eec8d81afc945489a3e5ee9515b1613`. Anonymous HTTP 200 and the live
HTML bytes were verified against Git HEAD after the Pages build. It describes
the current four-screen release and pending administration acceptance. Keep
private TAB setup/recovery documentation out of that public repository. Use this
prompt and `docs/master.md` for the detailed administration rollout status.
Use available authenticated tools for tenant work; verify current access instead
of assuming earlier sessions survive. Keep credentials out of chat and artifacts.
Follow current owner instructions for shared-history writes; do not infer new
commit/push authority from an old continuation block. Report actual validation
and distinguish documentation review from a production Audit.
