# App screen capture evidence — September 23, 2026

These four PNGs were captured directly from the running existing MILSTRIP Intake
Dev app in Power Apps Studio Preview. Capture bounds include only the app canvas;
browser tabs, tenant identifiers, profile controls and the Windows taskbar were
excluded at capture time. No UI reconstruction or pixel editing was used.

| Image | Visible state | SOP steps |
|---|---|---|
| 01-intake.png | Synthetic source pasted, Submit intake enabled | 1–2 |
| 02-results.png | Record 1 VALID; record 2 REJECTED with a short-record issue | 3 |
| 03-review.png | APPROVED saved, review version 2, canonical length 80 | 4–5 |
| 04-history.png | Matching REVIEW_DECIDED events, actor and record identifiers | 6 |

The sample used the known synthetic fixture pattern, fictitious requisition
`ZZ999926600002`, and a header explicitly identifying an SOP screen demonstration.
Request `852354ab-e97e-4315-b7d1-410beef6d756` was created only for these captures.
The first demonstration review recorded REJECTED at version 1; the second recorded
APPROVED at version 2. Both events therefore appear in History. History displays
event metadata, not the APPROVED/REJECTED payload; the SOP makes that distinction.

The final decision/version was read back from the approved local application
database. Cleanup required the exact request ID, original synthetic source text,
PASTE source type, application actor, two expected records and both expected
review versions. Only this request and its related application metadata were
removed, then absence was verified. No legacy operational table was written.

A separate agent visually reviewed all four images and checked the captions
against the actual controls. No credentials or personal/tenant chrome is visible.
The app remains unpublished; no screen formulas or tenant configuration changed.

The website embeds these images as data URLs; readers need no image downloads.
