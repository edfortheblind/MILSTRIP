# MILSTRIP Intake: local changes and TAB hosting roadmap

**Current deployment status:** See [master](../master.md) and
[native pilot acceptance](NATIVE_PILOT_ACCEPTANCE_2026-09-25.md). The implementation
and test snapshots below are historical; their pending flags are not current
deployment status. The hostname and database-migration roadmap remains applicable.

Owner requirements confirmed September 25, 2026. The historical implementation checkpoint includes
local implementation, saved unpublished native drafts and reviewed recovery of
the canceled sharing execution. Production database connections and Canvas
publication are not established by this document. Implementation verification
and separate recovery review are distinguished below.

## Deployment contract

The API, HTTPS endpoint and standard gateway run as services on always-on,
IT-managed TAB infrastructure. Normal use must work with the development laptop
powered off. Power Apps and Power Automate remain Microsoft-hosted; the gateway
connects those services to the TAB backend. This is the supported hybrid boundary
described in [Microsoft's gateway architecture](https://learn.microsoft.com/en-us/power-apps/maker/canvas-apps/gateway-reference).

Use the existing **Azure SQL Stage and Prod** first. The earlier requirement to
put every database immediately on an internal TAB VM is superseded. Later, move
both environments to prepared PostgreSQL destinations. The deployment path is
TAB-managed API/gateway plus existing vendor-managed Power Platform/Azure SQL;
costs include server operations, certificates, backups, database service and
existing Power Platform licensing. No additional connector or app is required.

The previous proposed API names `stage-milstrip.austinlighthouse.org` and
`milstrip.austinlighthouse.org` are planning inputs awaiting IT confirmation.
Power Apps player URLs remain the entry points. An internal API hostname alone
does not impose a network-location restriction on the Microsoft-hosted player.

## Identity and configuration

TAB SSO establishes identity; the application allowlist grants access. An enabled
TAB directory account alone does not grant application access. Verified identities
must have active app membership, app view permission and flow run permission.
Owners/Admins manage users and runtime configuration; Operators cannot see the
configuration navigation and are denied by the backend if they call it directly.
Administration remains accessible to authorized people when a business database
is unavailable. The existing broker and protected-owner rules remain in force.

Routine database setup happens inside **Power Apps > Configuration**:

1. Load the environment's configuration. Disable and apply the current profile
   before changing its database destination or initializing its schema.
2. Enter the replacement connection string privately, label the target, and save
   the draft. Provider `auto` detects PostgreSQL versus SQL Server/Azure SQL using
   the existing format/TLS validators. Blank keeps the saved connection/provider.
3. If application tables are absent or at version 1, type the displayed draft
   target and select **Initialize database**. The action adds only `milstrip_app`
   objects and upgrades supported version-1 metadata. It does not create a server,
   database, login, firewall rule or operational `dbo` object.
4. Test the draft. A pass validates connectivity, required application columns,
   schema version and the correct Stage/Prod marker. Test does not activate.
5. Apply the enabled draft with its fresh test receipt. Requests drain before
   activation; changed or expired receipts fail. Verify the environment and data.

Stored credentials are never returned to Canvas; replacement fields are masked
and cleared. Initialization uses the same command/status/retry mechanism as other
configuration actions. A failed or interrupted initialization is unconfirmed;
retry the same command. The additive operation preserves compatible data.

IT supplies database access and narrowly scoped schema permissions before setup.
An app administrator does not need to run Python, psql or a host configuration
screen. The source retains host recovery utilities for deployment maintenance;
they are not the routine app configuration interface.

## Intake contract

The owner selected **final review on every record**, a **two-hour** duplicate
window and an Admin/Owner override of that duplicate restriction.

- On the verified broker path, each person can have one unfinished intake per
  environment. Every record, including invalid records, needs an APPROVED or
  REJECTED decision. Invalid records cannot be approved. The parser's
  `completed_at` means parsing finished, not that operator review finished.
- **Resume / new intake** reads authoritative database state. It opens unfinished
  work or allows a fresh intake after all reviews are complete. Reloading the app
  or opening another tab does not bypass the backend check.
- Matching ordered normalized record content is blocked across all users in the
  same environment for two hours. Source/ticket IDs and email wrappers do not
  defeat the record fingerprint. Fixed-position spaces and record order remain
  significant. Stage and Prod have separate histories and checks.
- At exactly two hours, the duplicate window has elapsed. An override submission
  creates its own receipt and starts a new two-hour window for that content.
- Owners/Admins can select **Override 2-hour duplicate block**, enter a reason
  and submit. Authorization is rechecked on the server; the audit stores actor,
  reason, matching request and window. Override never bypasses unfinished review.
- An intake with zero extracted records is rejected and has no record reviews
  to finish. Identical zero-candidate input is still covered by the duplicate
  window. Unknown submission outcomes retain input and require reconciliation.
- A transaction holds the environment identity-row lock across checking and
  saving, preventing concurrent tabs/operators from both passing the check.
  This serializes submissions within an environment; monitor transaction times
  before increasing intake volume.

Schema version 2 adds `milstrip_app.intake_workflow`; existing source hashes,
request IDs, canonical records, decisions and audit history retain their meaning.
Initialization backfills existing requests with their original timestamps and
normalized fingerprints. The new gate applies to tracked broker submissions and
backfilled requests for the same recorded actor. Historical shared-credential
requests cannot be attributed retrospectively to individual TAB users. Review
remaining legacy work at the broker cutover rather than inventing ownership.

The published four-screen apps still use the legacy transport. Until broker-only
cutover, they do not enforce these new per-user workflow rules. Do not represent
local source readiness as deployed user protection.

## Hostname-ready deployment sequence

| Step | Action | Exit evidence |
|---|---|---|
| 1. Local preparation | Apply additive local schema, test both dialect contracts, generate Canvas/flow/connector artifacts | Passing tests, retained data preserved, no Azure SQL writes |
| 2. Close identity rollout | Canceled execution recovery is verified; accept finite native permission readback before sharing retries, then prove second-user behavior | Existing pending users and commands reconciled; role-denial and revocation checks |
| 3. IT host inputs | Confirm DNS/private IPs, certificates, service accounts, API/gateway placement, Azure SQL routing, backup/recovery and maintenance ownership | Approved host inventory and tested network paths |
| 4. Stage services | Install both provider drivers, run one API worker as a service, protect control files, configure HTTPS; migrate the existing gateway registration | Restart without interactive login; TLS and routing tests; laptop-off test |
| 5. Stage app acceptance | Load updated broker/Canvas source, bind the existing Stage flow, compile in Studio; enable broker-only control after identity acceptance | Authorized and denied users, in-app Initialize/Test/Apply, uncertain outcomes, two tabs, two operators, final review gate, duplicate override audit |
| 6. Azure SQL Stage | Configure the approved Azure SQL Stage string from the app; initialize the isolated application schema | Live SQL Server persistence, Unicode/padding, review replay/conflict, transaction rollback, timeout and schema-identity checks |
| 7. Azure SQL Prod | Back up; use the same accepted package and in-app setup for its independent database | Explicit release/cutover approval, Prod routing and authorized-user acceptance |
| 8. PostgreSQL Stage then Prod | Prepare and migrate schema/data, reconcile, freeze writes, disable old target, change the string in-app, Test/Apply | IDs/counts/canonical data/review versions/audit/workflow history match; accepted rollback/reconciliation plan |

The connector has one fixed host and broker credentials choose the environment.
Two DNS names do not by themselves split the running service. Keep this model for
initial relocation, or approve a separate Stage/Prod service topology before
changing connection bindings. Secure flow inputs/outputs and existing gateway
registration must be preserved.

## Database migration boundary

The app-side engine switch is a connection-string change; provider-neutral
repository operations handle both engines. A connection string cannot move data
or translate operational procedures. Before switching, the destination must have
compatible schema version 2, Stage/Prod identity and reconciled application data,
including workflow fingerprints and timestamps. Preserving those rows prevents
an engine change from clearing unfinished work or the two-hour duplicate window.
No operational legacy writer or SQL Server retirement is introduced here.

Validate Azure SQL live before claiming production portability; generated SQL
and PostgreSQL execution are not SQL Server behavioral acceptance. Keep schema
setup, migration and runtime activation separately recoverable even though
routine setup is initiated from the same Power Apps configuration screen.

## Verification and remaining gates

The final [pre-hostname validation](PREHOSTNAME_VALIDATION_2026-09-25.md)
records **580 passed, 0 skipped**, two upstream warnings, with local PostgreSQL in
151.18 seconds. The final API restart loaded the latest source and transient-503
mappings; retained counts and complete tracking are verified. The separately
reviewed [host recovery](SHARING_RECOVERY_IMPLEMENTATION_2026-09-25.md)
is **applied and verified**: the canceled execution is CLOSED and only its
matching lease was removed. The command, plan and user remain pending; authority,
profiles, memberships, observations and Management pacing are unchanged, and one
audit event was added. No active Management permit remains. The current blocker
is finite native permission-read acceptance before any sharing retry.

Both updated native Canvas drafts are saved, exported and unpublished. Separate
[native comparison](CANVAS_NATIVE_INTAKE_UPDATE_2026-09-25.md) verified each app's
85 controls, 724 properties, 37 handlers, six screen events and three App
properties, with only its matching broker. Baseline parser/literal-predicate and
accessibility diagnostics persist; native workflow acceptance remains open. No new
sharing grant, security cutover or Canvas publication is claimed. Recovery tests
passed 47 checks; separate combined review passed 160 with one PostgreSQL opt-in
test skipped. The correction-only and preceding results below remain historical.

The subsequent [tracking and retry correction](INTAKE_RETRY_CORRECTIONS_2026-09-25.md)
adds fingerprints for legacy-path submissions, read-only tracking-completeness
checks before activation and a successful configuration test, retained commands
on transient 503 responses and user-sharing conflicts, and exact source-receipt reconciliation for
uncertain intake submissions. No pending review does not prove an unknown
submission failed. Source text and duplicate-override state remain frozen until
the matching caller/source receipt is confirmed.

The combined correction regression run passed **117 tests; 44 database opt-in
tests were skipped**, with two existing dependency warnings in 31.35 seconds.
The new repository behavior was exercised in isolated in-memory SQLite;
target-database acceptance is separate. The local database opt-in environment
was absent, and this correction pass did not read private credentials or connect
to PostgreSQL/Azure SQL. Canvas generation and scoped whitespace checks passed.
The 458-test database-enabled result below belongs to the preceding increment.

Native Studio/player execution of these updated formulas, live Azure SQL verification,
finite permission-read and sharing acceptance, broker-only cutover, independent Audit and production rollout
remain open. No commit, push, cloud publication or DNS change is part of this
local increment.


Initial increment application evidence (historical):

- Schema version 2 applied to the approved localhost Stage database. Existing
  table counts were unchanged: 3 intakes, 5 records, 3 review decisions, 2 issues,
  6 audit events. Three historical workflow fingerprints were backfilled using
  original receipt timestamps. No operational tables were changed.
- The verified loopback API process was restarted with the new source. Its
  unauthenticated health request returns HTTP 401. Startup confirms the legacy
  runtime remains authoritative; this did not activate the blocked broker rollout.
- Canvas, flow, OpenAPI and connector generation checks pass. Roadmap links resolve.
- An intermittent pre-existing control-file atomic-replacement error surfaced in
  two test runs and passed on isolated rerun. The failure is reported as HTTP 503;
  its underlying filesystem cause is unconfirmed. Investigate host filesystem
  behavior before release; do not bypass atomic replacement or ignore save errors.

- Preceding increment full suite: **458 passed, 0 skipped**, 3 warnings in 89.52 seconds,
  with the approved local PostgreSQL integration environment enabled. Coverage
  includes real two-session submission races (same actor and cross-user duplicate),
  exact two-hour boundary, final review of every record, audited override,
  Operator denial, broker-driven resume/submit/review, version-1 upgrade/backfill,
  both SQL dialect contracts and existing regressions. Warnings are two upstream
  deprecations and an in-process pytest import-rewrite warning. Azure SQL was not
  contacted and native Power Fx execution was not part of this run.

**Status: DONE_WITH_CONCERNS** for local implementation and roadmap. Updated
Canvas drafts are saved and unpublished; native workflow acceptance, enforced-user
cutover and live Azure SQL acceptance remain release gates. The intermittent
control-file save failure remains an availability concern for host acceptance.
