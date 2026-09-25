# Screen provenance for edition 1.6.0

All five images are unchanged September 24 reference captures. No new native
screenshots were copied into the guide. The main procedure now follows reviewed
broker controls across Intake, Results, Review, History, Configuration and Users.
Stage 16 and Prod 6 are published for limited acceptance. These older images do
not document the newly published players or current administration screens.

The historical Intake image predates Resume / new intake and duplicate override;
the History image contains the former service actor. Current instructions require
the authenticated human actor. The host-editor image appears only in a historical
disclosure because broker-only activation has closed that editor. No current
Configuration/Users screenshot is claimed. Full capture evidence follows.

---

# App screen evidence — edition 1.4.0

**September 24, 2026.** Four PNGs were captured directly from the renamed
MILSTRIP Stage app in Power Apps Studio Preview. They show the same synthetic
intake and its review. The captures contain the app canvas only; browser tabs,
tenant controls and the taskbar are excluded. No UI reconstruction or pixel
editing was used.

| Image | Visible state | SOP steps |
|---|---|---|
| 01-intake.png | MILSTRIP Stage; STAGE / Ready; Check connection; synthetic source entered | 1–2 |
| 02-results.png | Persistent receipt for two records, one rejected; downstream delivery not connected | 3 |
| 03-review.png | APPROVED saved at version 1; canonical length 80 | 4–5 |
| 04-history.png | Matching REVIEW_DECIDED and intake REJECTED events | 6 |
| runtime-configuration.png | Native administrator screen using an Example Stage database target; no credentials displayed | Administrator configuration |

The Results image was recaptured after Stage publication and the API restart.
The completed load shows record 1 as VALID / APPROVED, record 2 as REJECTED /
NONE, the persisted receipt and enabled inspection controls.

The canvas fixture uses fictitious requisition `ZZ999926600001`, source header
`SYNTHETIC STAGE PUBLICATION TEST 2026-09-24`, and request
`ff3f3cb5-04f5-4135-af74-f8db41962673`. It remains in PostgreSQL with two
records, one APPROVED review and two audit events. History shows event metadata;
Review/Results supplies the saved decision. No cleanup was performed.

The earlier retained runtime request
`1d0c784d-c3bf-495c-928c-0b66687a58a4` also remains unchanged: one intake,
two records, two reviews and three audit events. The September 23 captures and
their removed fixtures belong to edition 1.2.0 and are superseded here.

Publication was verified by the tenant's **Publish successful** messages on
September 24: Stage at **1:01:57 PM**, Prod at **1:15:52 PM**. Both apps were
verified in the existing MILSTRIP solution; Stage retained its original ID.
The unchanged images show Studio Preview, not the published player or the new
administration screens. After these captures, licensing was verified for the
current administrator and Stage
passed connection and saved-results checks in the published player. Prod opens
with a separate connection, fixed environment and disabled database profile; it
cannot accept intake yet. New individual-user enforcement and in-app
administration remain pending native deployment acceptance.

The administrator image is a direct capture of the real Tkinter configuration
screen loaded with a separate demonstration configuration. Its `example-stage`
database name is illustrative. It does not establish a connection to that
database. The actual Stage connection test was verified separately; private
target details are excluded from the public image.

No passwords, connection strings, personal information or tenant controls are
visible. The guide embeds all five images and provides enlargement controls.
