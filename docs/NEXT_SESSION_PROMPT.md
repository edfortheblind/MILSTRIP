# Restart prompt ? September 25, 2026

Copy this into the next session in this repository:

```text
Resume MILSTRIP from the owner-requested September 25 release cut.
Read AGENTS.md, OWNER_PROFILE.md, docs/master.md,
docs/delivery/RELEASE_CUT_2026-09-25.md and
docs/delivery/FINITE_PERMISSION_READ_DESIGN_2026-09-25.md first.
Verify current Git/runtime/tenant state before relying on the checkpoint.

The objective remains: finish, verify and publish both Stage/Prod Power Apps
and the public guide; commit and push. This prompt resumes the explicit pause.
Prior implementation, browser/mouse/keyboard, normal TAB sign-in and publication
approvals persist. Keep progress brief and preserve independent design/review.

Core and guide commits are pushed. Guide 1.5.0 is live:
https://edfortheblind.github.io/milstrip-guide/
Both new Canvas drafts are saved/exported but UNPUBLISHED. Broker flows still
run older definitions. Latest full local suite: 747 passed, 0 skipped. This is
source evidence, not native release acceptance.

Immediate blocker: native Stage permissions page 1 returns 2 rows plus nextLink;
the earlier host result 3 was an aggregate. Native nextLink matches the fixed
host/path and has ordered keys api-version,%24filter,%24skiptoken. The current
single-page source fails closed but is insufficient. DO NOT import the private
single-page package or retry sharing with it.

Finalize/review the unfinished three-page design and strict cursor validator, then
implement bounded protected traversal with cumulative uniqueness, terminal
completeness, deadlines and write suppression. No cursor/row variables or
automatic pagination. Test limits and failure paths; independently review.
Prove protected native traversal for BOTH apps before updating broker flows.
Then finish pending memberships, actual second-user identity checks,
security/runtime activation, Studio Formula-error diagnosis and native workflow
acceptance. Publish accepted drafts and update/verify the guide accurately.
The historical canceled run was already recovered: do not repeat recovery or
clear leases. Last control state: 3 active, 3 pending, zero leases, security/runtime
inactive. Do not disable pending users to bypass activation.

Requirements remain: TAB SSO plus app-configured membership; Admin/Owner-only
Configuration and in-app DB Test/Apply/Initialize; every record needs a final
review decision before another intake; normalized duplicates blocked for 2 hours,
with explicit audited Admin/Owner override but no unfinished-review override.
Initial DB targets will be Azure SQL Stage/Prod, later PostgreSQL via connection
string/provider detection after schema/data readiness. API/gateway eventually
move to always-on TAB network hosts; Power Apps/Automate remain Microsoft-hosted.
Current work stays local: Stage PostgreSQL, Prod DB disabled, hostnames pending.
No operational SQL Server writes, DNS change or production DB cutover here.

Reuse existing resources and private artifacts named in the checkpoint.
Rediscover browser handles/tab order and foreground the browser before mouse
clicks. Avoid generic Close selectors. Never export tokens or unmask protected
permission rows. Do not retry the rejected SDK lookup; native UI already found
the diagnostic flow. Continue without repeating completed work or asking again
for already-granted approvals.
```
