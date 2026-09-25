# MILSTRIP operator guide

## [Read the published guide](https://edfortheblind.github.io/milstrip-guide/)

Edition **1.6.0**. Evidence date: **September 25, 2026**.
Pages deployment history records publication of this documentation edition.

Six operator steps cover Intake, Results, Review and History; the administration
section covers Configuration and Users. Select **View larger** to inspect the
reference screens or diagrams. The guide works in a browser without downloads
or sign-in.

**Stage 16 and Prod 6 are published for limited acceptance.** Six memberships,
native broker bindings and broker-only host authority are active. Both players
and licensing are verified for the current administrator only. Configuration,
intake completion, duplicate blocking and audited override passed. Prod's database
stays disabled; an initial post-consent startup stall recovered after one
read-only reload, with cause unproven. Second-user, role, intake-submission recovery
and diagnostic/accessibility checks remain pending.

The updated procedure requires every final record decision before a new intake,
blocks identical normalized content for two hours, and allows Admins/Owners to
override duplicates with an audited reason. Database configuration belongs in
the app; changing its connection string does not migrate existing history.

Production still requires managed network hostnames and Azure SQL acceptance,
followed by qualified PostgreSQL migration. Power Apps/Automate remain
Microsoft-hosted. Production handoff and downstream receipts are separate work.
The five dated synthetic reference captures predate the new controls and audit
identity; no fresh screenshots or credentials are included.

This repository publishes documentation only; it does not grant app access.
