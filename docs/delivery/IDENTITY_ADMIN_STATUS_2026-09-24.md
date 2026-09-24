# Identity and administration delivery status

**September 24, 2026: pagination trial canceled; sharing lease remains RUNNING; administration rollout withheld.**

This update adds administration to the existing Stage and Prod apps. It does not
establish production database readiness, a new SSO provider or shipment delivery.
The existing MILSTRIP solution, custom connector and on-premises gateway remain.

## Current tenant observations

The deployment lead verified these during this session:

| Area | Current result |
|---|---|
| Published Stage player | Licensing resolved; connection healthy; retained results read successfully |
| Published Prod player | Licensing resolved; opens and reports unavailable with database `DISABLED` |
| Prod destination | Independent target and activation authority still unanswered; no Prod activation performed |
| Corporate sign-in | Realm discovery reports `Managed` for `austinlighthouse.org`, under Travis Association for the Blind |
| Initial directory members | Live probe returned enabled internal-member records for all six approved people |
| Existing app ownership | Ed remains the verified platform Owner on both apps; this is separate from his in-app Admin role |
| Current grants | Claude and Mike have verified CanView access to both apps and run-only access to both flows; Ed retains platform deployment ownership and run-only access |
| Existing custom connector | Native readback shows eight operations, including `InvokeBroker`; the existing gateway remains selected |
| Broker connections | Management is Connected; both Stage/Prod broker references are bound |
| Imported broker flows | Both native definitions are Started; current references are bound |
| Private control state | Claude and Mike ACTIVE protected OWNER; Ed ACTIVE ADMIN; Kristen, Thomas and Shawn PENDING; security/runtime authority inactive |
| Canvas drafts | Both v2 drafts saved and natively exported; six screens, 81 controls and 679 source properties match each executable export; no direct API data source; neither published |
| Stage native checks | GetCurrentUser, GetHealth, ListUsers, GetRuntimeProfiles, Save draft and Test draft passed against the unchanged target |
| Prod native checks | SSO and administration/configuration reads passed with the database disabled |
| Protected run history | Metadata-only checks passed for two Stage runs; protected inputs/outputs remained unopened |
| Users-screen sharing | Final pagination trial stalled on its first Makers GET and was canceled; command pending, execution/lease RUNNING, no Management permit; earlier flow grants verified, app CanView grants absent |

The six initial people are Claude Furry and Mike Thompson as protected
application Owners, and Ed Lopez, Kristen Fleming, Thomas Stivers and Shawn
Hinkle as Admins. The protected owner sign-in names are
`claude.furry@austinlighthouse.org` and `mike.thompson@austinlighthouse.org`.
Directory object IDs, raw directory captures and credentials remain private.
No new Canvas version has been published and no control/security cutover has
occurred. The three active memberships were accepted through reviewed host
bootstrap verification of actual native permissions. The other three remain
pending; platform permissions alone do not activate a membership.

## Implemented in source

The broker verifies the person behind each request and evaluates current
application permissions for business and administration operations. Its fixed
Stage/Prod credentials select the environment. At explicit broker-only cutover,
legacy shared Basic credentials lose direct access to all seven business routes.

The flow obtains identity from an invoker-owned Office 365 Users connection and
uses private directory, broker and sharing connections. The app supplies only
an operation and payload. Internal sharing lease/callback operations are not
selectable by the app. Flow definitions suppress notification mail and protect
source data and replacement connection strings in run history. Metadata-only
inspection confirmed secure inputs/outputs on two successful Stage runs; it did
not open protected content or replace second-user identity acceptance. Exact run
evidence is in the [TAB sysadmin SOP](../TAB_SSO_SETUP_SOP.md).

The Configuration screen saves a draft, performs a read-only test and applies a
verified revision. Apply drains only the affected profile. Changing an enabled
database destination requires disabling that profile first. The single private
control store remains available when a business database is disabled. Provisioning
and data migration are separate from configuration.

The Users screen manages Admin and Operator access. Both application Owners and
Admins can configure the runtime and manage users; neither can alter the two
protected Owner entries. Addition remains pending until both app views and both
flow run-only grants are verified. Removal denies API use immediately. A durable
per-target lease prevents overlapping Stage/Prod sharing changes from reversing
one another. Unknown external writes require host recovery, not lease expiry.
Source also serializes calls to the shared Management connection with a durable
permit and a 13-second cooldown after confirmed completion. Unknown calls block
that permit. Six serial native calls observed post-completion intervals of at
least 13.516 seconds. Concurrent callers and response-timeout recovery remain
deployment acceptance work.

The explicitly verified deployment Owner's existing app permission counts as
view access without being edited. No other Owner/CanEdit exception is allowed.
Revoking that deployment owner's application access can leave platform cleanup
pending until IT transfers app ownership.

## Validation and review

The full source suite passed **372 tests; 73 database opt-in tests were skipped**,
with two upstream dependency warnings in 77.51 seconds. The skipped tests are not live database
acceptance, and source tests do not replace native tenant acceptance. The latest
pagination/flow/package/sharing batch passed **43 tests**.

The reviewer ran these focused checks:

| Check | Result |
|---|---|
| Flow source, management pacing and sharing leases | 33 passed: 12 source, 14 pacing and 7 lease checks; includes loopback API dispatch |
| Host launchers and solution package | 19 passed: 14 host checks and 5 package tests |
| Bootstrap initialization and identity mapping | 9 passed |
| Stale-import activation guard | 6 passed independently; source mismatch or absence leaves control unchanged |

The focused results above record individual review passes. Native deployment
acceptance remains incomplete.

Independent review identified and corrected three recovery defects:

- Active control startup initially depended on legacy configuration/verifiers.
  Startup now reads the active control authority directly.
- A persistent lock file could block all writes after process death. Lock
  ownership now belongs to the OS, which releases it when the process exits.
- Bootstrap initially wrote membership and imported runtime profiles separately.
  Initialization now assembles both before one atomic file creation.

A separate reviewer identified the overlapping Add/Remove platform race. The
per-target sharing lease and unknown-outcome handling address it in source and
regression tests. Flow-source tests are the flow author's validation, not an
independent audit of that author's work.

Independent in-memory package inspection against the native baseline verified
two Off workflows, six connection references, five ZIP members, deterministic
bytes and exclusion of existing canvas/connector payloads. This check did not
write a package or import it. Subsequent native import of the latest pacing
definitions is verified; both native flows are now Started.

Independent native-export comparison verified each draft's six screens, 81
controls, 679 source properties, startup/events and matching flow binding. App
Checker reported zero formula errors and two literal-predicate warnings. Each
export also contains 66 accessibility findings: 27 focus indicators, 35 tab stops
and four icon labels. These remain publication-review items. The scalar
`ParserErrorCount=1` was also present in both earlier published exports; SARIF
contains no corresponding parse or syntax finding. Its meaning is unresolved.

The latest v2 exports preserve those counts and contain four verified UI fixes:
the role list shows OWNER only for a protected Owner; its default preserves that
role; Users clears unrelated messages while retaining pending-command guidance;
Configuration does the same without dropping a pending command or saved draft.
See the [native Canvas evidence](CANVAS_SOURCE_ASSEMBLY_2026-09-24.md) for exact
exports and hashes. The fixes do not constitute published-player acceptance.

## Current sharing blocker

Kristen's command `689cf9a0-cfe5-4fc7-9496-bb1e2db0c32c`, plan
`b68690a1-837a-44ce-9950-248e4eb52df4`, remains pending. Three earlier executions
reported `READBACK_PAGINATED_STAGE_APP`, including after app-permission GET was
aligned to API version `2017-06-01`. Both flow run-only grants are verified;
neither app CanView grant was added. The app permissions remain the three
bootstrap principals: Ed as platform Owner, Claude and Mike as CanView.

The final built-in pagination trial, native run
`08584113137259107903122568693CU13`, started at
`2026-09-24T23:39:19.5961106Z`. It completed Save_membership and Acquire_lease,
then stalled for over eight minutes at `Before_add_stage_app`. No permission
mutation or Management call occurred. The deployment lead canceled the run around
23:48 UTC; the native UI confirmed cancellation.

Durable execution `fe7ea517-271b-4393-bfd0-f51657b9f99e` and lease
`6ddd23d7-e3b6-458e-adfa-967bf5d91c81` still report RUNNING. No Management permit
is held. Native cancellation did not complete the API reconciliation. Do not
clear the lease, fabricate a completion callback or resume native retries.
Independent design/review of canceled-run reconciliation and finite permission
readback is required next. See the [pagination evidence](MAKERS_PERMISSION_PAGINATION_2026-09-24.md).

Advisory independent recovery review accepts the preserved state as a safe, fail-closed
handoff. A future evidence-checked host procedure must prove terminal native
cancellation, that every grant mutation never started, exact
plan/revision/lease/execution identity and absence of an active Management call.
It may close only the aborted execution, leaving membership pending. This is a
recovery requirement, not an implemented or executed procedure.

Memberships remain three ACTIVE and three PENDING. No security/runtime authority
was activated, no new Canvas version was published and this attempt made no
business-database write. OAuth works; this is an implementation blocker.

Public guide **1.4.0** is live from commit
`af9334de8eec8d81afc945489a3e5ee9515b1613` in `edfortheblind/milstrip-guide`.
The Pages build completed at 23:32:24 UTC; anonymous HTTP returned 200 and matched
the committed HTML exactly. It retains the published four-screen workflow and
marks administration acceptance pending. This private status and the TAB SOP
were not exported to the public site.

## Release work remaining

1. Design and independently review canceled-run reconciliation and bounded
   permission reads. Preserve the held lease and partial grants. No further native
   attempts until this recovery path is accepted; then reconcile the same command.
2. Verify a second authorized user's identity and audit actor. Accept denied-user,
   Operator, protected-owner and wrong-profile behavior in the tenant.
3. Complete configuration Apply, partial-sharing, timing, unknown-outcome and
   retry acceptance. Save/Test against the unchanged Stage target has passed;
   target switching is not accepted.
4. Review accessibility findings, complete explicit server cutover and verify
   direct legacy calls are denied. Publish accepted versions and verify their
   standalone players.

Prod database selection remains a separate owner decision. Azure SQL provider
support is implemented, but no live Azure SQL acceptance or production source
write is established. A later VM move needs its own approved target, network and
certificate arrangements.

The [administrator SOP](../RUNTIME_CONFIGURATION.md) includes a draft request for
optional HTTPS redirect names and a separate future internal API hostname. No
DNS, redirect or SSO configuration change has been performed.

Sources: [ADR 0006](../adr/0006-user-identity-and-administration.md),
[implementation contract](IDENTITY_ADMIN_IMPLEMENTATION_CONTRACT_2026-09-24.md),
[flow artifacts](../../powerapps/flows/README.md),
[canvas artifacts](../../powerapps/canvas/broker/README.md).
