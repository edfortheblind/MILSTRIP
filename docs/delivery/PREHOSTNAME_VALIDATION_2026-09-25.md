# Pre-hostname implementation and validation evidence

**Date:** September 25, 2026

**Status:** DONE_WITH_CONCERNS — local corrections and canceled-run recovery verified; native sharing acceptance remains blocked.

This evidence checkpoint records the deployment lead's current local validation
and restart results. It supplements the [hosting roadmap](INTAKE_NETWORK_ROADMAP_2026-09-25.md),
[intake corrections](INTAKE_RETRY_CORRECTIONS_2026-09-25.md) and
[applied sharing recovery](SHARING_RECOVERY_IMPLEMENTATION_2026-09-25.md). Earlier test
counts in those documents remain historical evidence for their source snapshots.

## Local implementation and verification

- All newly created intakes, including the legacy published-app path, record
  workflow fingerprints in their original transaction. Per-person review and
  duplicate restrictions remain enforced on the verified broker path. Schema,
  environment and tracking-completeness checks guard enabled-profile activation
  and successful configuration tests. Shared historical actors remain shared.
- Lock contention and profile-drain contention return transient 503 responses
  and retain the configuration command. Definite configuration 409 conflicts
  release the rejected command so a stale draft can be discarded. Access-sharing
  commands still retain 409 outcomes because membership may already be saved.
  An uncertain intake remains blocked until its exact
  caller/source receipt is found, including completed and zero-record intakes.
  Generated Canvas source retains the text and override state during uncertainty.
- Future sharing lease requests bind native flow/run identity in source. This
  does not retrofit identity into the already canceled historical execution.
- The final full approved local PostgreSQL run passed **580 tests, 0 skipped**,
  with **two upstream dependency warnings in 151.18 seconds**. Earlier runs of
  504 and 519 tests and the 29 flow/lease tests describe preceding snapshots.
  Recovery implementation passed **47 tests**. Separate combined collector,
  recovery, lease, Management and control review passed **160 tests, with one
  opt-in PostgreSQL test skipped**, in 61.75 seconds and found no remaining code
  blocker. These focused results supplement the final 580-test combined run.
- The final API restart loaded the updated tracking writer and transient-503
  mappings. Post-restart readback preserved **3 intake
  requests, 5 records, 3 review decisions, 2 validation issues, 6 audit events
  and 3 workflow rows**. Tracking is complete. Unauthenticated health returns
  **HTTP 401**. Existing historical rows were retained. Private control readback
  confirms **zero sharing leases, three active and three pending memberships**;
  `security.enforced` and `runtime.active` are both false.
- Both updated six-screen native drafts are saved, exported and unpublished.
  Separate [native comparison](CANVAS_NATIVE_INTAKE_UPDATE_2026-09-25.md) verified
  **85 controls, 724 source properties, 37 behavior handlers, six screen events
  and three App properties in each app**, with only its matching broker.
  Baseline diagnostics remain in both: **Parser 1, Binding 0**, two SARIF
  literal-predicate findings and 66 accessibility items. Source equivalence is
  distinct from acceptance of all workflows in Studio and the published player.

These results establish local source and PostgreSQL behavior. They do not
establish live Azure SQL behavior or complete execution acceptance of the updated
Canvas drafts in Power Apps Studio and the published player.

## Native evidence collection and recovery boundary

The finite **read-only metadata collector is implemented**. It validates fixed
routes and continuation scopes, follows pages within explicit limits, projects
safe metadata, and keeps offline fixtures distinct from native evidence. An
isolated inspection of Microsoft's installed request primitive confirmed the
30-second request timeout and disabled redirects reach the transport. The
independent implementation review found two defects: a permission assignment
from a different app could verify access, and a later transport failure could
retain a previous HTTP status. Both were corrected and their targeted
regressions passed. Protected action input/output content was not required.

Fresh native collection resolved the historical proof limitation through the
definition attached to the exact canceled run. Both logical-flow references
match Stage; its reviewed definition hash and all **225 unique definition/action
names** agree. All **16 permission mutations, 16 Management actions and 32
Management reservation/completion actions** were explicitly skipped. Membership
save and lease acquisition succeeded before the canceled first permission read.
The genuine native workflow-version field remains null; no version is invented
and the currently deployed definition is not substituted for run-attached proof.

**Atomic host recovery was independently reviewed, applied and read back.** The
deployment lead used the reviewed CLI after a fresh preview and another fresh
SSO-authenticated collection. Exact preview revision/digest, current Admin
authority, historical bindings and Management checks passed. Readback confirmed:

- The historical execution is **CLOSED** and its matching lease is removed.
- The command, sharing plan and membership remain **pending**.
- Users, security, runtime profiles, resources, Management pacing and retained
  plan observations have unchanged hashes. Exactly one audit event was added.
- No active Management permit exists; no permission grant or sharing retry occurred.

The safe private result is `.cred/sharing-recovery-after-20260925.json`.
The [implementation evidence](SHARING_RECOVERY_IMPLEMENTATION_2026-09-25.md)
records the applied preview revision and semantic digest. This supersedes the
earlier checkpoint's statement that recovery was unimplemented and the lease
still held. The finite, complete **native interactive permission-read path** is
now the sharing blocker; host metadata collection and lease recovery do not
establish that path's acceptance.

## Remaining release gates

1. Accept a finite, complete native app-permission path before another sharing
   attempt. The host collector does not by itself repair interactive sharing.
2. Complete pending sharing, second-user/role acceptance, configuration Apply
   and uncertain-outcome checks; resolve or accept the recorded native diagnostics
   and validate the updated draft workflows.
3. Enable broker-only enforcement and publish only after those acceptance gates.
   Azure SQL Stage/Prod acceptance and TAB-hostname deployment follow the roadmap.

The verified host recovery is the only access-control state transition recorded
here. No new sharing grants, security cutover or Canvas publication was performed.
No hostname/DNS change or Azure SQL production connection is claimed. Both app
drafts remain unpublished; native UI acceptance remains pending.
