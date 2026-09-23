# Canvas implementation evidence — 2026-09-23

## Executed changes

Windows desktop automation operated the existing Brave Power Apps Studio session.
App ID `7f1b64d0-d51a-4ec8-84ad-2b18fe8c2f82`, MILSTRIP Intake Dev, was verified
from the Studio URL and title. The existing Default environment, custom connector
and MILSTRIP-DEV-LAPTOP gateway were retained. No new app was created.

Added scrIntake, scrResults, scrReview and scrHistory from the source files in
`powerapps/canvas/`; preserved the original Screen1 scaffold. Imported the original
image as `milstrip-app`; each new screen displays it. Set App.StartScreen to
scrIntake. Studio reported Saved (Unpublished). The original image was also selected as the
app-level icon and verified in General settings. Publication was not performed.

Studio exposed the connector's actual required argument order:

- CreateIntakeRequest(source_text, source_type, optional-fields-record).
- CreateReviewDecision(record_id, command_id, decision, expected_version, reason).

Nullable latest_review is Dynamic; its decision is explicitly converted with Text.
Review refresh retrieves the typed record instead of patching incompatible Dynamic
and record types. Canonical text uses the supported font string "Courier New".

Connector results assigned with Set must then be evaluated inside IfError before
continuing. Otherwise an error stored in a variable can permit later success
messages. Each network result now forms a separate guarded value/replacement
pair, followed by the success branch. See Microsoft's
[error handling reference](https://learn.microsoft.com/en-us/power-platform/power-fx/error-handling).
Studio's retired "Disable formula-level error management" switch was Off.

## Connection correction

The app used the connection created at 10:56 AM, while the owner's successful
GetHealth test used the separate existing connection created at 1:20 PM. The
Connections details page confirmed the latter had no associated apps. Both used
the same connector and gateway. The latter was renamed to
`MILSTRIP Local Dev API - verified gateway` to distinguish them.

The app's original connection was updated with the privately stored credential,
after an in-process verifier comparison and direct local HTTP 200 check. No secret
was printed, copied to documentation or committed. This resolved the app's 401.
The app data-source name remains MILSTRIPLocalDevAPI. Neither connection was deleted.

## Runtime evidence

The corrected error branch was exercised by the existing 401: input stayed in
place, the message reported an uncertain outcome and Submit was disabled until
explicit reconciliation. No new request appeared in the local database.

After correcting the existing connection, Studio preview passed:

- Synthetic mixed input created request `5b7416e5-1108-4c1e-a2b8-4a34ab5bfbc4`.
- Request details and records showed record 1 VALID and record 2 REJECTED.
- Review displayed canonical length 80, including trailing spaces.
- APPROVED synthetic review advanced record 1 from version 0 to version 1.
- With APPROVED selected, Save review was disabled for the rejected record.
- History showed REVIEW_DECIDED and intake events attributed to milstrip-app.
- Recent request listing contained this same request.

The standalone HTTP workflow already covers exact retry, stale/changed-command
409, pagination, invalid approval, authentication and scoped synthetic cleanup.
These backend checks are distinct from the live canvas checks above.

## Solution and backup verification

The existing MILSTRIP solution initially contained only the custom connector.
Adding the existing canvas app was initially rejected because Studio held its
editing lock. After saving and leaving Studio, Add existing ? App ? Canvas app ?
Outside Dataverse succeeded. Solution Objects now lists MILSTRIP Intake Dev
(`tab_milstripintakedev_7a2a6`) and the existing custom connector. No duplicate app,
solution, connector or gateway was created.

A functional draft backup was downloaded to
`%LOCALAPPDATA%\MILSTRIP\backups\MILSTRIP-Intake-Dev-20260923-implemented.msapp`
(1,188,631 bytes). ZIP integrity passed; 50 control formulas matched the repository
sources after whitespace normalization. This backup precedes app-icon selection
and solution association, but includes the final functional screen formulas.
The initial 19,560-byte scaffold backup is on the Windows Desktop. Backups remain
outside Git and contain no private credential file.

After runtime verification, only this run's request, two records, review and audit
rows were removed. Cleanup required an exact request ID, UUID source marker,
synthetic source text and authenticated actor match. The review was independently
read back as APPROVED, version 1, actor milstrip-app before cleanup. Prior test
requests and all operational tables were untouched.

## Remaining acceptance

Two formula warnings concern intentional empty-gallery filters; no formula errors
remained before the final runtime pass. Accessibility and layout refinement,
canvas conflict/retry and outage tests, and multi-page canvas navigation remain
separate checks. The standalone HTTP test covers the underlying backend cases. This is an unpublished development draft, not a production
rollout or independent Audit. No legacy operational writes were performed.

Status: **DONE_WITH_CONCERNS** ? functional development increment implemented and
verified; the additional UI acceptance cases above remain before shared rollout.
