# Makers permission pagination: implementation and acceptance

**September 24, 2026: native pagination trial stalled and was canceled; user administration is not accepted.**

**September 25 update:** The evidence below preserves the original trial.
Current generated source removes the stalled aggregation policy, and independently
reviewed host recovery has closed the canceled execution and released its lease.
Membership remains pending; the finite interactive permission-read path is still
unaccepted. See the [current validation](PREHOSTNAME_VALIDATION_2026-09-25.md)
and [applied recovery evidence](SHARING_RECOVERY_IMPLEMENTATION_2026-09-25.md).

The authorized Kristen sharing command remains pending. In the preceding three
executions, native reads succeeded but the returned continuation marker
prevented complete app-permission verification. The diagnostic reported `READBACK_PAGINATED_STAGE_APP`; changing
the permission-read API version to `2017-06-01` did not resolve it. Flow run-only
grants were verified, while both app grants remained unverified. No permission
check was bypassed.

The actual Microsoft Makers connector metadata advertises
`x-ms-pageable: {"nextLinkName":"nextLink"}` for `Get-AppRoleAssignment`.
The generator now adds `runtimeConfiguration.paginationPolicy.minimumItemCount`
of `1000` to those reads only: eight actions per flow. Secure inputs/outputs,
disabled retries, fixed app IDs, API versions and environment-scoped edits are
unchanged. No custom HTTP action or manual continuation-URL handling was added.

Microsoft documents this native pagination setting as a retrieval threshold.
It is a **minimum, not a hard transport cap**; fetching whole pages can exceed
the threshold. The application therefore still requires fewer than 1,000 rows,
no `nextLink` or `@odata.nextLink`, successful read/filter actions and one
matching plan resource. Incomplete or oversized results remain unverified.
[Pagination behavior](https://learn.microsoft.com/en-us/azure/logic-apps/logic-apps-exceed-default-page-size-with-pagination),
[runtime configuration](https://learn.microsoft.com/en-us/azure/logic-apps/logic-apps-workflow-actions-triggers#runtime-configuration-settings)

## Final native trial

The final bounded trial used the same pending Kristen command. It completed
`Save_membership` and `Acquire_lease`, then remained at `Before_add_stage_app`
(the first Makers GET) for more than eight minutes. No permission mutation or
Management call began. The deployment lead canceled the test in the native run
UI around 23:48 UTC; the UI confirmed **Canceled**.

| Reference | Recorded value |
|---|---|
| Native run | `08584113137259107903122568693CU13` |
| Started | `2026-09-24T23:39:19.5961106Z` |
| Command | `689cf9a0-cfe5-4fc7-9496-bb1e2db0c32c` |
| Sharing plan | `b68690a1-837a-44ce-9950-248e4eb52df4` |
| Durable execution | `fe7ea517-271b-4393-bfd0-f51657b9f99e` - RUNNING |
| Durable sharing lease | `6ddd23d7-e3b6-458e-adfa-967bf5d91c81` - RUNNING |
| Management permit | None held |

Native cancellation did not reconcile the durable execution. The command stays
pending. Earlier flow run-only grants remain verified; neither app CanView grant
was added. Three memberships are ACTIVE and three are PENDING. Security/runtime
activation and new Canvas publication remain withheld; this trial performed no
business-database write.

## Required next work

Stop the native retry loop. Preserve the execution, lease, command and partial
grants. Do not clear the lease or fabricate a completion callback. Obtain an
independent design/review for verified canceled-run reconciliation and a finite,
complete permission-read path before another tenant attempt.

Advisory independent recovery review accepts this preserved state as a safe, fail-closed
handoff. Future host recovery must verify all of the following before changing
control state:

- The native run has a terminal canceled result.
- Every permission-grant mutation never started.
- The plan, revision, lease and execution match the retained command exactly.
- No Management call is active.

Recovery may close only the aborted execution and must leave membership pending.
This evidence-checked procedure is not implemented or executed in this delivery.

Neither the small-result continuation marker nor the stalled aggregation has a
confirmed cause. Connector metadata and passing source tests do not establish
native pagination behavior. Keep complete-readback guards and protected run
content intact. OAuth connections work; no IT policy or SSO change is requested.

Validation: the full source suite recorded **372 passed, 73 database opt-in
skipped**, with two upstream warnings in 77.51 seconds. The prior focused pagination, flow,
package, diagnostic and sharing-lease batch passed **43 tests** with the same two
warnings. The private package is under `.cred/broker-supported-pagination/`.
These checks do not establish native acceptance.
