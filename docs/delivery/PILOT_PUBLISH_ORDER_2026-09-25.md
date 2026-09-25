# Pilot publication order — September 25, 2026

**Status: approved sequencing; publication and acceptance require separate evidence.**

The owner has authorized publishing both existing apps and the guide. This order
uses that authorization without widening the approved six-person audience or
granting maker/co-owner rights. It corrects earlier checklists that required a
view-only user's execution of an unpublished draft before publication. Actual
second-user identity remains mandatory for full release acceptance.

## Why publication precedes the second-user app check

Microsoft distinguishes saved drafts, available to app editors, from the Live
version that shared users run. Publishing delivers changes to everyone already
sharing the app; it is not a private preview for one tester.
[Save and publish canvas apps](https://learn.microsoft.com/en-us/power-apps/maker/canvas-apps/save-publish-app)

Studio Preview requires opening the app for editing. Live Monitor's **Connect
user** opens a published app; **Invite** lets another person observe a session
and does not make them its caller. Neither supplies view-only execution of our
unpublished drafts. The repository contains no verified alternative supported
tester path to the Power Apps V2 brokers. The manual permission diagnostic uses
embedded connections and cannot prove a different caller's invoker connection.
[Preview an app](https://learn.microsoft.com/en-us/power-apps/maker/canvas-apps/preview-app),
[Collaborative Live Monitor](https://learn.microsoft.com/en-us/power-apps/maker/monitor-collaborative-debugging)

## Complete before either app is published

1. Accept the bounded native permission reader for both apps. Deploy the reviewed
   broker definitions to their existing IDs, explicitly activate the reviewed
   brokers before any app calls, and verify their actual On state, protected
   history and connection references. Office 365 Users caller
   identification must remain **Provided by run-only user**; the other
   connections remain private and embedded.
   [Run-only connections](https://learn.microsoft.com/en-us/power-automate/create-team-flows)
2. Refresh each draft's binding to its matching updated flow and verify the saved
   dependencies and formulas. Adding a connector can leave cached flow metadata
   stale. Microsoft's development procedure removes/readds the updated flow and
   saves the app; perform native readback after any binding change. Complete this
   before invoking in-app sharing.
   [Power Apps flow integration](https://learn.microsoft.com/en-us/troubleshoot/power-platform/power-apps/connections/best-practices-when-updating-a-flow)
3. Preserve and verify the three already-active memberships with completed
   current plans; reconcile only the three pending memberships through the app.
   Require all six current memberships `active` and their current sharing plans
   `completed`, with no unresolved sharing execution or Management permit. Ed
   must not Save access on his own row: the self-access guard rejects that action.
   Another Admin/Owner must perform any needed change to Ed's access. Preserve
   recovered historical plans and audit records; old noncurrent `pending` records
   are not current membership failures. Verify only the approved individual
   app-view and flow-run grants; preserve existing legitimate deployment ownership.
4. Back up the reviewed state and complete explicit host broker-only activation
   against the current control revision. Restart the API; verify security and
   runtime authority are active and legacy shared Basic calls are denied. This
   activation affects both apps. Their old published direct-API versions may be
   unavailable during the controlled cutover window; do not reopen that bypass.
5. Complete Ed's native draft acceptance: Configuration Save/Test/Apply and
   uncertain-command handling; intake receipts, final-review completion,
   duplicate blocking/override and recovery, with the exact native scope recorded
   in [observed recovery evidence](#observed-recovery-evidence-for-this-limited-pilot). Apply requires the preceding
   activation and restart. Keep the current local Stage target and Prod database
   disabled; no hostname, Azure SQL activation or migration is part of this step.

## Publish for the existing audience, then verify

1. Publish the accepted updated Stage and Prod versions to their existing app IDs.
   Their audience remains the same six configured people. Do not add users,
   groups, Everyone grants, maker rights or co-ownership. Publishing updates the
   version available to every existing recipient; there is no claimed two-user
   pilot switch.
   [Share a canvas app](https://learn.microsoft.com/en-us/power-apps/maker/canvas-apps/share-app)
2. Verify Ed's standalone players load the new versions, the correct environment
   and expected administration. Confirm Prod still reports its database disabled.
3. Have another approved TAB user sign in normally with their own Office 365
   Users connection, retaining only app view and flow run-only platform rights.
   Exercise both published apps. Verify the API identity and an appropriate
   audited acceptance action belong to that person, not Ed or the shared broker.
   Complete the remaining role, denied-user, revocation and recovery checks using
   actual authorized test sessions; an asserted actor or Ed's session is no substitute.
4. If that person is unavailable, record **Published for limited acceptance;
   second-user verification and full release acceptance pending**. Preserve the
   outstanding gate and do not claim verified multi-user operation or complete
   release acceptance. Publication itself does not satisfy the gate.

## Observed recovery evidence for this limited pilot

The resumed native checks encountered genuine uncertain responses during user
sharing, Configuration Apply and review Save. Status reconciliation and exact
retained-command retries were verified for those paths. Intake submission itself
returned definite results, so its separate source-receipt recovery path has not
been observed natively. Source tests cover that path; they are not native evidence.

The prepublication recovery evidence must name the paths actually exercised.
Limited publication under the sequence above retains the intake-submission case,
second-user identity and the remaining multi-user matrix as explicit full-release
acceptance gaps. Do not manufacture an outage, discard an unknown source ID,
resubmit with a new identity, or describe these gaps as passed. Duplicate rejection,
audited override and completion of every test-intake record must pass before
publication. See [native acceptance](NATIVE_PILOT_ACCEPTANCE_2026-09-25.md).

## Guide and evidence

Publishing the public guide only publishes static documentation. It does not
publish the apps, grant app/flow access or enable Prod's database. Update the guide
to the observed app status and record published versions, native checks and any
remaining acceptance limits separately. Do not present planned or single-account
checks as completed second-user evidence.

This note changes sequencing only. It does not report that cutover, publication
or second-user acceptance has happened, and it introduces no new platform resource.
