# Existing MILSTRIP canvas app

Target app ID: `7f1b64d0-d51a-4ec8-84ad-2b18fe8c2f82` (owner supplied).
Verified name: MILSTRIP Intake Dev. Environment: existing organization Default.
Solution: existing MILSTRIP; the existing app was added and membership read back.

The four `*.controls.yaml` files are the source controls applied to this existing
app through Windows desktop automation on 2026-09-23. Studio confirmed Saved
(Unpublished). The original Screen1 scaffold remains. StartScreen is scrIntake.
The original image is imported as `milstrip-app` and displayed on all four screens.

Live canvas acceptance passed synthetic intake, recent request listing, request
details, mixed valid/rejected results, an APPROVED review at version 1, rejection
of approval for invalid input, and authenticated audit history. The canonical
valid record remained 80 characters. See [execution evidence](../../docs/delivery/CANVAS_IMPLEMENTATION_2026-09-23.md).

## Reapply source controls to the existing app

1. Verify the app ID using the [setup SOP](../../sop/powerapps-setup.md).
   Download a copy of the saved app before editing. Inspect existing screens
   and preserve any work already present.
2. The existing connector is already updated. Add its working connection through
   **Data → Add data**. Do not recreate the connector or repeat its setup.
3. The owner's Studio screenshot confirms the data-source identifier
   `MILSTRIPLocalDevAPI`. All four control sets now use that exact identifier.
   Optional operation parameters are expressed as records.
4. Use a 1366 × 768 tablet layout. Create or reuse blank screens named
   `scrIntake`, `scrResults`, `scrReview` and `scrHistory`.
5. Import `assets/milstrip-app.png` through Media; retain resource name `milstrip-app`.
   Select the same image in the app's icon settings.
6. Copy each matching controls file, select its screen in the tree and paste
   code. Do not paste duplicate controls onto a populated screen.
7. Set **App.StartScreen** to `scrIntake`. Enable formula-level error management
   if disabled. Do not add an OnStart reset of inputs or pending commands.
8. Resolve App checker errors and save this same app. Shared publication is
   outside this development increment.

Microsoft documents the [code-view paste workflow](https://learn.microsoft.com/en-us/power-apps/maker/canvas-apps/code-view)
and [v3 source schema](https://github.com/microsoft/PowerApps-Tooling/blob/master/schemas/pa-yaml/v3.0/pa.schema.yaml).
Schema validation does not validate control properties, connector binding or
Power Fx execution; those checks require Studio.

## Behavior and acceptance

- Intake preserves pasted text. An uncertain submission blocks another submit:
  load recent requests and compare its displayed source ID before explicitly
  allowing a new submission. Intake POST is not idempotent; blind retry can
  duplicate a request.
- Results load request details, records and issues, keeping validation and review
  separate. Pagination retrieves all records. Switching request hides stale
  results until load succeeds. Canonical values are never trimmed or rebuilt.
- Results retain the saved-intake receipt after refresh and review. It shows
  Request ID, received time and initial validation counts; reopened requests use
  matching details without borrowing another request's totals. Delivery remains
  disconnected. Mixed/empty intake and cross-request checks passed in Studio;
  see the [acknowledgement update](../../docs/delivery/ACKNOWLEDGEMENT_DESIGN_2026-09-23.md).
- Review creates one UUID per decision and freezes the payload while its outcome
  is unknown. Retry resends the same body and record ID. A 409 requires explicit
  reload; only successful reload clears the pending command, retaining the reason
  for operator inspection before a new decision.
- History pages request-scoped events. Failed pagination retains the current
  cursor and values. Approval never authorizes delivery.
- Basic username identifies the development connection, not the Power Apps
  signed-in user. Do not share this connection as a multi-user review system.

Verify in Studio: synthetic intake, 80-character canonical values including
trailing spaces, rejected-record approval denial, exact review retry, two-client
version conflict, audit history, all pagination and gateway/API outage recovery.
Capture sanitized statuses only, never authorization headers or raw orders.

Input and pending commands persist only while the app stays open. Browser
restart loses in-memory state; check recent requests/history before resubmission.
This increment does not persist sensitive input in offline device storage.

## Studio execution confirmed

The agent applied these control sources using the existing Studio session,
corrected the app's existing connection credential and saved the unpublished
draft. App checker had no formula errors and two empty-gallery warnings. The
original Screen1 was preserved. The original image is both the app icon and the
header image on each new screen. The app now belongs to the existing MILSTRIP
solution. A verified local `.msapp` backup contains the original functional
increment. The later receipt changes are saved in Studio and in these source
controls; that earlier backup predates the receipt change.
