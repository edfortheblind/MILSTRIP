# MILSTRIP broker flows

These are deterministic **source drafts**, not evidence of a deployed identity
boundary. Stage and Prod use separate flows and private broker connections to the
existing MILSTRIP custom connector and gateway. The generator does not deploy,
share, start a flow, send mail, or change a database.

**September 25 release cut:** do not import the current single-page candidate
for sharing acceptance. Native Stage returns two rows plus a continuation;
bounded traversal remains unimplemented. See the
[paused checkpoint](../../docs/delivery/RELEASE_CUT_2026-09-25.md).

## Build and bind

```powershell
.\.venv\Scripts\python.exe scripts\build_broker_flows.py
.\.venv\Scripts\python.exe scripts\build_broker_flows.py --check
.\.venv\Scripts\python.exe -m pytest tests\test_broker_flows.py -q
```

Copy `bindings.example.json` into private deployment storage. Supply the verified
tenant/environment IDs, verified deployment-owner object ID, existing app IDs, two actual flow IDs, solution connection
reference logical names, and connection instance names. No passwords belong in
the bindings file. Set `management_metadata_verified` only after confirming the
operation metadata in the intended environment. Then generate outside the source
tree:

```powershell
.\.venv\Scripts\python.exe scripts\build_broker_flows.py --bindings .cred\broker-flow-bindings.json --output .cred\broker-flow-build
```

The output is solution cloud-flow `clientdata`: serialize the **whole JSON
document** into the Dataverse workflow's string field. Workflow category is 5,
type is 1, and primary entity is `none`. Import/update in Draft/Off state first.
Do not replace existing app, connector or gateway IDs. Connection reference rows
must exist in the same solution before the flow is activated.
[Microsoft's cloud-flow code interface](https://learn.microsoft.com/en-us/power-automate/manage-flows-with-code)

## Trust and connection settings

| Reference | Runtime source | Purpose |
|---|---|---|
| invoker | Provided by run-only user | Office 365 Users `MyProfile_V2`; establishes the caller's object ID |
| directory | Private deployment connection | Resolves that ID and verifies enabled internal membership; resolves new access targets |
| broker | Private connection, distinct per app | Calls only `InvokeBroker`; server fixes tenant and Stage/Prod profile |
| makers | Private deployment connection | Grants/removes CanView on the two fixed apps |
| management | Private deployment connection | Grants/removes run-only access on the two fixed flows |
| permissions | Private deployment connection | `shared_webcontents` / `InvokeHttp`; reads only the fixed app-permission URLs |

The permission reader uses **HTTP with Microsoft Entra ID (preauthorized)** with
base URL `https://api.powerapps.com` and resource URI
`https://service.powerapps.com/`. Its connection is embedded; it is not an app
data source or a run-only user's connection. The solution package contains seven
connection references: five shared references and two private broker references.

The app passes only `operation` and `payload_json`. The flow never trusts a passed
actor, object ID, role assertion or trigger header. `AcquireSharingLease`,
`RecordSharingResult`, `ReserveManagementCall` and `RecordManagementCall` are
internal operations. Only flow actions construct them
from API-issued plans, execution IDs and management-connector readback.

Adding access requires exact corporate UPN resolution. Removing access uses the
existing server-stored membership; a deleted or disabled directory object does
not prevent removal. The API denies a removal immediately. Additions remain
pending until all four resource grants are verified. The explicitly bound,
verified deployment Owner already has app view access; that exact Owner grant
counts as present without being edited. Other Owner/CanEdit grants remain
unsatisfied and require administrator reconciliation. Removing the deployment
owner denies API access immediately, but platform cleanup stays pending until
IT transfers ownership. The flow never transfers or downgrades ownership.
A server lease serializes sharing
work for each target across both flows. An older execution must finish before a
new removal can change platform grants; API denial remains immediate. A failed
or timed-out external write retains an unknown-outcome lease. It must not expire
into a second writer. Host recovery must first establish that the earlier flow
and its external actions have stopped. App grants use
`NotifyShareTargetOption: DoNotNotify`.

Every Power Automate Management call first reserves one server-held permit
shared by both apps, then waits for its server-issued time. The permit stays
held through the call; confirmed completion starts a 13-second cooldown before
another call. This enforces the connector's five-calls-per-60-seconds limit for
MILSTRIP's shared connection. Do not reuse that private connection for unrelated
workflows. A competing execution remains pending; an unknown call holds the
permit for host recovery. There is no timed takeover. The timestamp-only Wait
action carries no directory, source or credential data.

Pagination, a failed read, and an incomplete response never prove that permission
is absent. Partial sharing remains pending. Retry the same command ID or inspect
`GetAdministrationOperation`; do not create a new command to hide an unknown
outcome. Connector retries are disabled, including writes. The flow returns
`ok`, `status`, `request_id`, `result_json`, `error_code`, and `error_message`.
`ok` means the operation returned; inspect the returned sharing status before
displaying “access active.”
Pacing and connector latency can exceed the app's response window. Preserve the
command ID and check its status after a timeout; a timed-out app response does
not establish that the flow stopped or the membership change failed.

Sharing readback now returns a fixed diagnostic code for the first affected
resource, such as `READBACK_PAGINATED_STAGE_APP`. Codes distinguish a plan
mismatch, failed read/filter, pagination, the row limit and a permission that
does not match the requested state. They contain no principal, URL or response
body. Deploy the API's expanded error-code allowlist before the updated flow;
otherwise its callback will fail validation. This instrumentation preserves the
existing verification gates. A native retry identified
`READBACK_PAGINATED_STAGE_APP`. The earlier Makers read used its documented
`2017-06-01` default; that version change did not resolve the native continuation
marker. The September 24 native pagination trial stalled and was canceled.
The candidate source now replaces each of the eight app reads per flow with a
single fixed, environment-filtered `InvokeHttp` GET. Makers edits retain
`2016-11-01` and the fixed deployment-environment filter.

The protected parser requires a direct JSON object or JSON text containing a
`value` array. An unexpected response wrapper, error envelope, failed parser,
malformed assignment, cross-app ID, wrong tenant or duplicate assignment or
principal makes the page unverified. A page must contain fewer than 1,000 rows
and neither continuation marker. Target grants must belong to a User; CanEdit
and unpinned Owner grants keep cleanup pending instead of becoming verified
absence. No automatic pagination or retry is enabled. The native response shape
and route still require acceptance before deployment; see the
[finite-reader design](../../docs/delivery/FINITE_PERMISSION_READ_DESIGN_2026-09-25.md).
The historical canceled execution
has been reconciled and its matching lease released, without adding permissions.
Do not retry sharing until a finite, complete interactive permission-read path
is accepted. See the [historical pagination evidence](../../docs/delivery/MAKERS_PERMISSION_PAGINATION_2026-09-24.md)
and [current validation and recovery](../../docs/delivery/PREHOSTNAME_VALIDATION_2026-09-25.md).

## Evidence and remaining acceptance

The wrapper, `PowerAppV2` trigger and `OpenApiConnection` shape match the native
MILSTRIP Stage broker export from September 24, 2026. Its sanitized structural
fixture is in `schema/native-powerapp-v2-baseline.json`. Management request
schemas were extracted from Microsoft's tenant connector Swagger on the same
date, without connection details or user data.
Native designer Save on September 24 required the nine `InvokeBroker` body
leaves as `body/...` parameter keys. The generator now uses those captured keys
and omits the whole-object `body` parameter; actor leaves still come only from
the verified directory result. Prior whole-object runtime success did not prove
designer compatibility. The corrected package needs native Save and run checks.
`schema/native-run-only-permissions.json` preserves the native permission-record
shape with synthetic IDs. `/flows/users` returns principal membership without a
`roleName` field; the tests confirm that this counts as run-only access while a
retained owner record remains separate.

Microsoft's published Logic Apps schema does not recognize Power Automate's
`PowerAppV2` and `OpenApiConnection` extensions. Static tests validate built-in
structure with those extensions projected to supported forms, then test native
extensions, bindings, trust boundaries and management bodies separately. This
does not replace service import validation or a real flow run.

Before exposing either app, verify all of these in the tenant:

1. Run-only settings use the invoker's Office 365 Users connection and private
   connections for the other five references. Verify with a second authorized
   user; the returned actor must change with the caller.
2. Directory reads return `accountEnabled`, `userType`, ID, UPN and display name.
   Missing fields or lookup failure must deny access.
3. Secure inputs/outputs hide source records, directory results, credentials and
   replacement connection strings throughout run history. Compose, Parse JSON
   and Response use secure inputs; Microsoft hides their outputs accordingly.
4. Test add/remove, partial sharing, readback failure, overlapping commands in
   both apps and existing deployment-owner rights. Confirm a late older Add
   cannot run after a completed newer Remove, and the API never activates an
   unverified addition.
   Verify management pacing in native run history, including delayed execution,
   concurrent Stage/Prod calls, throttling, and a response timeout followed by
   status recovery. The source tests do not establish tenant timing acceptance.
5. Test an unlisted corporate user, disabled user, forged actor payload and direct
   legacy Basic call. Activate broker-only API enforcement before app exposure.
6. Bind each app to its matching flow, preserve the fixed environment formula,
   and verify a Stage operation cannot reach Prod. A disabled business database
   must still allow authorized configuration and user administration.

Microsoft references: [run-only connections](https://learn.microsoft.com/en-us/power-automate/create-team-flows),
[Office 365 Users](https://learn.microsoft.com/en-us/connectors/office365users/),
[Power Apps for Makers](https://learn.microsoft.com/en-us/connectors/powerappsforappmakers/),
[HTTP with Microsoft Entra ID](https://learn.microsoft.com/en-us/connectors/webcontents/),
[Power Automate Management](https://learn.microsoft.com/en-us/connectors/flowmanagement/),
[secure run history](https://learn.microsoft.com/en-us/azure/logic-apps/logic-apps-securing-a-logic-app),
[Wait Until action](https://learn.microsoft.com/en-us/azure/logic-apps/logic-apps-workflow-actions-triggers#wait-action),
[workflow schema](https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json).
