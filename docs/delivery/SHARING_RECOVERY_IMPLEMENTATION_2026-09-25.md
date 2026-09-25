# Host recovery implementation

**September 25, 2026 — reviewed live recovery applied; native sharing acceptance pending.**

The deployment lead applied the reviewed host transition after a fresh native
preview and another fresh SSO-authenticated collection during apply. The preview
control revision was `fdce5ebc-7063-4b74-b675-3493142624fe`; the matching semantic
evidence digest was
`6240170454f014a1353c26a1988844199668e095b56b68a2f6d427a20431639a`.
Readback verified the historical execution is **CLOSED**, its matching lease is
removed, and the command, plan and membership remain **pending**. Hash comparisons
confirmed users, security, runtime profiles, resource bindings, Management pacing
and retained plan observations are unchanged. Exactly one audit event was added;
no active Management permit exists. The safe private readback receipt is
`.cred/sharing-recovery-after-20260925.json`.

No sharing retry, permission grant, security cutover or Canvas publication
followed this recovery. The current blocker is acceptance of a finite, complete
native permission-read path before interactive sharing resumes. The historical
held lease is no longer a blocker.

`api/sharing_recovery.py` implements the narrow transition in the
[reviewed recovery design](SHARING_RECOVERY_DESIGN_2026-09-25.md). It accepts only
the pinned historical Stage run, command, plan, execution and lease, with the
independently reviewed run-attached definition snapshot and full action inventory.
The snapshot identity does not invent a native workflow-version field.

The host service requires fresh authenticated collection, an active application
Admin/Owner, exact current state bindings, a canceled terminal run and 225 matching
definition/action names. All 16 permission mutations, 16 Management calls and 32
Management reservation/completion actions must be explicitly skipped. The two
reviewed membership/lease calls must have succeeded before the canceled first
permission read. Unknown or additional external actions fail validation. This
initial implementation deliberately rejects missing action rows instead of
inferring nonexecution from an ancestor.

`scripts/recover_sharing.py` defaults to live **preview** through the fixed
Microsoft-authenticated PowerShell collector. It does not receive passwords,
tokens, arbitrary URLs or caller-supplied native assertions. The optional
`--offline-evidence` mode only qualifies a captured metadata file without writing
state; it cannot be combined with `--apply`.

Applying requires explicit `--apply`, the preview's `--expected-control-revision`
and `--evidence-digest`, and another fresh live collection. The semantic digest
excludes collection time; each collection independently must be no older than
five minutes and later than cancellation. A changed revision or changed proof
requires a new preview. No native collector or recovery command was executed as
part of implementation testing.

Within one existing `ControlStore.mutate`, recovery closes only the canceled
execution and removes only its held lease. It records provenance, native run
identity, evidence timestamps and digest, and one safe audit event. Membership,
plan, command, observations, protected owners and actual grants remain unchanged.
An active Management permit or any reservation for this lease blocks recovery;
unrelated completed reservations remain intact. Identical replay returns the
stored result without another write. Late broker callbacks cannot replace the
recorded host outcome. An unconfirmed apply reports an unknown change result and
must be reconciled with the same command and approval values.

Validation uses synthetic temporary control files and a synthetic collector.
The captured native projection passed structural/action validation at its
original collection time without reading or changing the real control store.
Independent review identified and corrected an explicit `None` revision that
could otherwise disable compare-and-swap; missing and malformed approval values
now fail before collection or mutation. Tests also cover stale/changed proof,
unsafe actions, actor/plan changes, Management activity, partial-observation
preservation, unrelated leases, persistence failure, replay and late callbacks.
All **47 recovery tests passed**. The combined recovery/lease/pacing run reported
70 passes and one existing lease-test failure at the private control-file save;
that test passed on its isolated rerun. This repeats the previously recorded
intermittent host save concern and is not presented as an uninterrupted full-suite
pass. The preceding 70-test run passed before the final preservation test was
added. Both runs emitted the same two existing dependency deprecation warnings.

The separate design/review agent then reviewed the final transition, revision
binding, collector boundary and CLI and reported no remaining code blocker. Its
combined collector/recovery/lease/Management/control validation passed **160
tests, with one opt-in PostgreSQL test skipped**, and the same two warnings in
61.75 seconds. The intermittent save failure did not recur in that run. These
checks preceded the fresh live preview and verified transition recorded above;
they do not establish native sharing acceptance.

After recovery and the final corrections, the deployment lead's complete local
PostgreSQL run passed **580 tests, none skipped**, with two upstream warnings in
151.18 seconds. The API was restarted with the final source. Both native Canvas
drafts were saved and exported without publication; their separate comparison
and remaining diagnostic limits are recorded in the
[native update evidence](CANVAS_NATIVE_INTAKE_UPDATE_2026-09-25.md).
Final control readback confirmed zero sharing leases, three active and three
pending memberships, and both security enforcement and runtime authority still
inactive. Business database counts and complete workflow tracking were preserved.

**DONE_WITH_CONCERNS:** implementation passed separate review and the narrowly
scoped live recovery is applied and verified. Native permission reads, sharing
completion, second-user acceptance, per-user cutover and publication remain gates.
