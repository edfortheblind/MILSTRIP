# App screen evidence — edition 1.2.0

**September 23, 2026.** Four fresh PNGs were captured directly from the existing
MILSTRIP Intake Dev app in Power Apps Studio Preview. The captures contain only
the app canvas; no browser tabs, tenant/profile controls or taskbar. No UI
reconstruction or pixel editing was used.

| Image | Visible state | SOP steps |
|---|---|---|
| 01-intake.png | Synthetic source entered; Submit intake enabled | 1–2 |
| 02-results.png | Persistent saved receipt; one VALID and one REJECTED record | 3 |
| 03-review.png | APPROVED saved at version 1; canonical length 80 | 4–5 |
| 04-history.png | Matching REVIEW_DECIDED event and record identifier | 6 |

The capture fixture uses fictitious requisition `ZZ999926600003`, source header
`SYNTHETIC RECEIPT DEMO 2026-09-23`, and request
`660ee537-9552-44ad-bfc6-165f83873954`. There is one APPROVED review at version 1.
History shows event metadata; the decision is read back in Review/Results.

The implementer verified the saved decision against the approved local database.
Cleanup matched the exact request, source, actor, source type, record count and
review version before removing that request and its related application rows.
The separate zero-candidate receipt test
`24cc56d9-ceec-4f72-8206-f90d17cf1525` was removed with equivalent fixture guards.
Absence of both requests was verified. No legacy operational table was written.

The existing app's receipt formulas were updated and saved. Studio reported all
changes saved at **16:35:37**; the app remains **unpublished**. A separate
`acknowledgement_review` agent checked the four images against the instructions.
No credentials or personal/tenant chrome are visible. The website embeds the
images, so readers do not download them separately.
