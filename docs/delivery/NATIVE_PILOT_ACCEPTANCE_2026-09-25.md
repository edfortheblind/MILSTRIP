# Native pilot acceptance — September 25, 2026

**Status: Stage 16 and Prod 6 Live for limited acceptance.**
This checkpoint records native checks by the current administrator. Independent
second-user identity and full release acceptance remain pending. All six current
memberships are active and host broker-only activation has completed; native
post-restart identity, administration reads and Configuration acceptance passed.
Both synthetic intakes are fully reviewed; genuine review retry, normalized
duplicate rejection and audited override passed. Both published players and
licensing are verified only for the current administrator; other users' licensed
player sessions remain unverified. Guide publication is a separate documentation
operation and does not establish additional app acceptance. Guide 1.6.0 was
subsequently published as public commit `17173e1`; Pages and exact committed-HTML
HTTP verification passed. See the [guide verification](../operations-guide/VERIFICATION.md).

The implementation checkpoint is `925478e`. The full local suite passed
**1,003 tests, none skipped**, with two upstream warnings, including approved
local PostgreSQL integration. See the [master document](../master.md) and
[native permission-reader evidence](NATIVE_PERMISSION_VALIDATION_2026-09-25.md).
Local tests and read-only permission traversal do not establish every native
application workflow.

## Saved bindings and native administration before host cutover

| Check | Stage | Prod |
|---|---|---|
| Binding update | Native Refresh | Removed the existing broker from the app and readded that same broker |
| Independent exported-rule comparison | All 4,367 existing rules unchanged | All 4,367 existing rules unchanged |
| App startup | Completed | Completed |
| Business environment | Ready | Unavailable as expected while its database is disabled |
| Administration | Enabled | Enabled |
| Load users | Succeeded | Succeeded; six configured users returned and the button reenabled |
| Load configuration | Not recorded in this checkpoint | Succeeded; existing PostgreSQL target displayed Disabled |

The refreshed bindings continue to reference the reviewed existing brokers.
The native export comparisons and source checks found no unintended formula
change. These checks cover the current administrator's draft session, not another
person's invoker identity or publication of the saved drafts.

Prod's business-workflow request produced the expected native failure at
`Invoke_operation`: "This environment is disabled; contact the administrator".
Its completed startup and successful user-list request confirm that authorized
administration remains available while the business database is disabled. The
failure is not evidence of a broken administration binding or successful Prod
data access.

## Membership progression

At **19:09:04 UTC**, before the first new reconciliation, the recorded membership
snapshot was **three active and three pending**. That is a historical snapshot.

At **19:11:16 UTC**, one of the pending administrator memberships completed its
native app reconciliation. The UI displayed **Access: active | Sharing:
completed**. Independent state review verified all four desired-present grants,
the completed current plan, a CLOSED execution, zero sharing leases and no
Management permit. Membership totals became **four active and two pending**.

The next pending administrator's **Save access** encountered a genuine
synchronous response timeout. The app retained the same command. The first
**Check command status** returned pending while the native flow was still
running; no retry or replacement command was submitted.

At **19:17:34 UTC**, independent control-state review confirmed that membership
active, its current plan completed, all four desired-present grants verified,
execution CLOSED, and zero leases or Management permit. Totals became **five
active and one pending**. A subsequent status check on the retained command
displayed **Access: active | Sharing: completed**. The command cleared,
**Check command status** and **Retry sharing** became disabled, and **Save
access** became available again. No retry or resubmission was needed.

The native run itself ended at the 120-second response timeout; it is not recorded
as Succeeded. The durable change and same-command UI readback succeeded. This
verifies genuine native user-access recovery after an uncertain response.
Configuration-command recovery passed later as recorded below; intake-submission
recovery remains a separate pending acceptance check.

At **19:22:18 UTC**, the last pending membership was independently verified active
with its current plan completed, all four desired-present grants verified, a
CLOSED execution, zero leases and no Management permit. Its UI call succeeded
synchronously, displayed active/completed and cleared the command without a retry.
All **six memberships are active; none remain pending**. Historical recovery
records are preserved; old noncurrent pending plans do not override completed
current membership plans.

## Host preflight and activation

Independent read-only preflight at **19:19:25 UTC** found both imported profiles
exactly matched the selected legacy authority across revision, provider, label,
connection string and enabled state. No connection values are reproduced here.
The approved loopback PostgreSQL Stage target passed health, all seven required
tables, schema version 2, Stage identity and complete workflow-tracking checks.
Prod remained disabled and was not connected. No provisioning or database write
occurred; both private configuration files were unchanged by this preflight.

After UI and sharing work were idle, the identified API was stopped. Activation
against the reviewed exact control revision succeeded at **19:24:13 UTC**.
Independent comparison with the private backup found only both authority flags
changing from false to true, the control revision, and one `BROKER_ONLY_ENFORCED`
audit event. All other control state and the legacy runtime file were preserved.

`ValidateOnly` passed with the worker stopped. The API restarted through
`Start-LocalApi.ps1` using the same selected paths and one worker. Anonymous
health returned HTTP401; direct health with Basic credentials returned HTTP403
before credential verification; invalid broker credentials returned HTTP401.
This is negative-boundary evidence, not a test using verified valid legacy
credentials.

Both apps subsequently completed native startup after the restart. Stage showed
Ready against the retained local target with administration enabled. Prod showed
the expected Unavailable business state with administration enabled; its user
list returned all six memberships ACTIVE.

Stage **Load configuration** passed. **Save draft** returned SAVED with a blank
replacement string and the existing enabled target retained. **Initialize
database** stayed disabled even after the exact saved draft target was typed.
Applying before Test reached the native operation and returned HTTP412
PreconditionFailed, but the response exceeded the synchronous 120-second limit.
Both active profiles and revisions remained unchanged. The UI retained the same
command, blocked new changes, and its first status lookup found no confirmed
result. After the native operation was terminal, one retry used that exact frozen
rejected Apply command. The definitive **Command rejected** response then cleared
the pending command, disabled status/retry, and enabled Test while retaining the
original saved draft. No Apply record or active profile change occurred. This
passed both the missing-test guard and genuine configuration uncertainty recovery.

The native **Test draft** passed with a receipt created at **19:37:25 UTC** and
expiring at **19:42:25 UTC**. Independent review matched the exact draft, revision,
base, digest and authenticated human actor. **Apply draft**, invoked at
**19:38:20 UTC**, returned APPLIED and cleared the draft. Exactly one Save/Test/Apply
sequence completed under the actual human identity, bound to that unexpired
successful test. Only Stage's revision changed; its label, provider and enabled
state stayed the same. Prod remained unchanged and disabled; all six memberships,
sharing and the legacy runtime file were unchanged. No Initialize operation ran.
The post-Apply health/workflow check completed successfully: Stage was Ready
against its retained local PostgreSQL target, with administration enabled.
Configuration acceptance for this existing local target is complete, including
the Initialize guard, missing-test rejection and actual uncertain-response
recovery. This does not qualify a new Azure SQL target or initialize a database.

## Native intake and review acceptance

The synthetic Stage intake submitted at **19:41:01 UTC** stored exactly one
receipt containing two records: one VALID and one validation-REJECTED. Its actor
was the authenticated human administrator; previously retained data remained
intact. No duplicate override was requested for this original submission.

The first record's APPROVED decision persisted once, but its native response
became uncertain. Retrying the exact retained review command returned **Review
saved**, version 1. Independent database review found exactly one decision and
one corresponding audit event; retry created neither a second review nor a
second audit event.

With the second record still undecided, source input and Submit remained disabled.
The Admin's duplicate-override checkbox itself remained enabled, but checking it
and providing a reason did not unlock source input or Submit. **Resume / new
intake** reopened the same unfinished request. The invalid record could not save
an APPROVED decision.

The second record's REJECTED decision completed. Both final decisions had version
1 with one audit event each; pending records became zero and the workflow allowed
starting another intake. This verifies final-review completion and the unfinished
intake guard, including when an administrator selects duplicate override.

After completing the original intake, a CRLF and terminal-newline variation was
submitted without override. The app displayed a definitive duplicate-blocked
message. Independent state review at **20:07:35 UTC** found no additional receipt
or changed counts and exactly one matching intake inside the two-hour window;
an older historical match was outside that window. This verifies native normalized
duplicate rejection within two hours for the current administrator. Cross-user
enforcement remains covered by local tests, not a second native user session.

Selecting override with an empty reason kept Submit disabled. An override with a
nonblank reason was submitted once at **20:08:20 UTC** and returned a distinct
saved two-record receipt with the same normalized fingerprint. Independent
verification found exactly one override audit event with the authenticated human
actor, the exact supplied reason, the prior request link and a two-hour window.
The previous request cohort was unchanged. This verifies the authorized override.

Final independent preflight at **20:12:35 UTC** found both new intakes completed:
four reviews, four unique commands and four review audit events, all at version 1,
plus the one override audit. The workflow was clear and the prior request cohort
was preserved. Six memberships had completed current plans, zero leases and no
Management permit; both authority flags were active and Prod remained disabled.
The final native **Resume / new intake** cleared the form and showed Ready.

An uncertain intake-submission outcome was not observed. Its native recovery
remains pending and is not inferred from the separately verified configuration,
user-access and review-command uncertainty recoveries.

## Publication and standalone players

Stage **version 16** showed Publish successful at **20:14:26 UTC** and Live.
Prod's **Publish this version** confirmation was requested at **20:16:34 UTC**;
the Publish successful message and **version 6 Live** were observed around
**20:17 UTC**. Both retained their
existing app identities and six-person audience; no sharing change accompanied
publication.

After publication, the old cached Stage player displayed a real direct-connector
denial from `MILSTRIPLocalDevAPI.GetHealth`: "Direct API access is disabled; use
the verified application broker". This is the observed old-player path, separate
from the earlier HTTP probe rejected before credential verification. Refresh
loaded the new version. The administrator allowed its Office 365 Users connection
at **20:17:45 UTC**; Stage then showed Ready and Configuration Load returned the
existing enabled Stage profile.

Prod initially stalled during startup after ordinary Office 365 Users consent.
One read-only browser reload completed startup; the cause of the stall is
unproven. Configuration and Users became enabled, business access remained
disabled, and Configuration Load returned the existing disabled profile. No
configuration mutation occurred during these player checks. These results verify
both standalone players for the current administrator, not flawless startup or
another person's connection and licensing.

A further read-only check in the published Stage player passed: **Load recent
requests** reopened the retained override receipt. **Load / refresh history**
completed and displayed two `REVIEW_DECIDED` events, one `DUPLICATE_OVERRIDE` and
the intake `REJECTED` event. No mutation accompanied this navigation or history
read. This additional evidence does not change the outstanding acceptance gates.

## Remaining release gates

Follow the approved [pilot publication order](PILOT_PUBLISH_ORDER_2026-09-25.md):

1. Verify another approved user through their own sign-in, license and invoker
   connection. Complete remaining role, denied-user and revocation checks.
2. Observe and accept native uncertain intake-submission recovery separately from
   the passed configuration, user-access and review recovery cases.
3. Resolve the exported Parser finding and accessibility review. Native Studio
   showed no formula errors and two literal-predicate warnings; the exported
   Parser counter remains unexplained and is not classified as an exporter
   artifact. The 66 accessibility items per app remain open.

Publication does not complete these gates or establish full multi-user release
acceptance. Managed hostnames, Azure SQL runtime qualification and production
data migration remain outside this local pilot.

The aggregate evidence above comes from the private
`.cred/native-canvas-binding-acceptance-20260925.json` record, subsequent native
milestone/state reviews and independent source review. Identity values,
command/run identifiers, credentials and native
screenshots remain outside this document.
