# Public documentation release verification — September 23, 2026

Scope: reading edition **1.1.0**, current-state SOP and proposed two-period plan.
This verifies documentation, not application UAT or independent production Audit.

## Editorial result

A separate agent reviewed the original guide and the revision: **PASS, no
must-fix findings**. Its recommendations and applied changes are recorded in
[EDITORIAL_REVIEW.md](EDITORIAL_REVIEW.md). Full engineering detail remains in
the private companion notes; the public guide leads with status and six steps.

## Build and reading checks

- Opened a lone copy of `index.html` in an isolated browser directory: no sibling
  dependencies, no HTTP requests, no browser errors.
- Seven inline charts, six SOP steps, embedded SVG downloads and section anchors
  passed. Native disclosures, modal opening and Escape closing were exercised.
- Print expands every disclosure. Rendered chart text fits node/viewport bounds;
  page overflow checks passed at 390 and 1440 pixels.
- Full PDF: **12 pages** (previous edition: 20). Quick SOP: **two pages**, with
  the complete action sequence on page 1 and all recovery cases on page 2.
- Independently inspected the rendered desktop guide and quick-SOP page layouts.
- PDF text and metadata passed the public identifier checks; source-ID intake
  recovery and same-command review retry are present in both PDFs.
- The packaging agent ran 11 temporary-fixture checks, including deterministic
  ZIP/checksum output, exact file allowlist, private references and offline links,
  status/date/anchor checks, optional SOP handling and unrelated-output protection.
- Final build and package commands passed; whitespace/diff checks passed.

## Published artifact verification

Public repository: <https://github.com/edfortheblind/milstrip-guide>.
It hosts the public guide HTML and reading README. The implementation repository remains private.

Release: [guide-v1.1.0](https://github.com/edfortheblind/milstrip-guide/releases/tag/guide-v1.1.0),
targeting public documentation commit `6a0237c00d1a4b31d043d799f1c64d5da247aeee`.
Read back as published, not draft or prerelease.

Unauthenticated HTTP requests returned **200** for the release page and all six
assets: standalone HTML, illustrated PDF, quick-SOP PDF, complete ZIP, README and
SHA256 manifest. Every downloaded asset's SHA256 matched the local release file.
The ZIP uses an explicit allowlist; private notes, evidence, runtime sources,
credentials, deployment identities and order data are excluded.

## Evidence boundaries

Current app claims retain their September 23 evidence date. This work did not
re-query Power Platform or production databases. The app remains a saved,
unpublished development draft; Phase 2 publication and database cutover are plans.
The freeze, delivery route, identity/hosting, capacity/recovery and acceptance
decisions remain open. No runtime or tenant configuration was changed.

The owner explicitly authorized public artifact preparation and commit/push for
this increment. Rebuild and packaging commands are in [README.md](README.md).

## Webpage delivery correction

The owner clarified that the deliverable must open as a webpage. GitHub Pages
now publishes the public repository's `main` root, with `.nojekyll` and HTTPS
enforced. The primary URL is <https://edfortheblind.github.io/milstrip-guide/>.
Public documentation commit: `46b32b8fe331b3c7243f3250c90e437d5b47eddc`.
Download-first instructions were replaced with this direct link. Existing release
assets are optional archives, not the reading workflow.

Live verification passed: anonymous HTTPS **200**, `text/html`, exact match to
committed HTML bytes, six SOP steps, seven inline charts, section navigation,
diagram viewer/Escape close, and 390/1440-pixel layout with no browser errors.
A separate agent independently confirmed the anonymous webpage and embedded
content. GitHub reports the Pages build as `built`.

## Screenshot SOP update — web edition 1.1.1

The owner requested the app screens within the SOP. Four authentic app-only
captures now accompany the corresponding actions: Intake (steps 1–2), Results
(3), Review (4–5) and History (6). The modal supports both screenshot and diagram
viewing, including Escape close and responsive layout. Images are embedded, so
the webpage requires no additional downloads.

The existing development app was exercised with one isolated synthetic intake.
The final APPROVED review at version 2 was independently read back, then this
request and only its related application rows were removed and absence verified.
No legacy operational tables, app formulas or tenant configuration were changed.
The app was not published. See [capture evidence](screens/README.md).

A separate agent visually reviewed all four public images and matched them to
the control labels. Browser/tenant/profile chrome was excluded at capture time.
The History wording now accurately describes REVIEW_DECIDED event metadata;
the saved decision itself is confirmed through Review/Results.

The isolated HTML build passed four decoded images, six SOP steps, seven diagrams,
all four screenshot modals, chart modal, print expansion, anchors, rendered chart
bounds, zero external requests/browser errors, and 390/1440-pixel page overflow.
Visual inspection confirmed the screenshot/instruction layout. Both PDFs contain
all four screenshots: the full guide is now **15 pages**, and the screen-based SOP
is **five pages**. These supersede the earlier page counts for edition 1.1.0.
Public text/PDF checks and allowlisted packaging also passed.

The updated public site is sourced from commit
`cedf2c76b9f5e2d7bef3c31551f5163ec4aebb98`. The existing 1.1.0 downloadable release
remains an unchanged archive; the primary deliverable is the updated webpage.

Live readback passed anonymous HTTPS 200 and exact committed-byte equality.
All four screenshots loaded at their expected resolution; all four full-size
viewers, six-step structure and desktop/mobile layout passed in an isolated
browser with no JavaScript errors. GitHub Pages reported the new commit built.

## Intake receipt and editorial revision — web edition 1.2.0

The existing app now retains an **Intake saved** receipt on Results: Request ID,
received time and initial validation totals. It explicitly displays **Delivery:
not connected**. Matching request details restore the ID/time receipt for a
reopened request; counts are omitted when the original acknowledgement belongs
to another request. The API and connector contracts are unchanged.

Native Studio Preview checks passed: mixed intake (two records, one rejected),
zero-candidate intake, results refresh, saved approval at version 1, matching
history event, and reopening the first request while the newest acknowledgement
belonged to the second. No counts from that second request appeared. Database
readback confirmed both saves and the review. Cleanup verified exact source,
actor, type, record counts and review version before removing only these test
rows; absence was read back. Studio reported all changes saved at 16:35:37 local
time. The app remains unpublished; the solution, connector and gateway were reused.

Four new app-only captures document one synthetic request throughout the SOP.
A separate agent inspected each image and found no publication blockers.
The principal editorial agent rewrote the guide; a second agent checked control
labels, outcomes, recovery and current/proposed claims. Initial-validation count
wording, item-lookup terminology and the accepted/rejected downstream receipt
distinction were corrected. [The editorial standard](EDITORIAL_STANDARD.md)
requires that review before future publication, with word limits and exact-label
checks. The [acknowledgement design](../delivery/ACKNOWLEDGEMENT_DESIGN_2026-09-23.md)
specifies production evidence and unresolved integration contracts.

The complete build passed: four decoded screen images, six SOP steps, seven
charts, screenshot/chart modals, Escape closing, disclosures, print expansion,
anchors, rendered SVG bounds, no external requests/browser errors and no page
overflow at 390/1440 pixels. Both printable editions were regenerated: 12-page
guide and four-page SOP. Allowlisted packaging passed; the webpage remains the
primary deliverable.

Edition 1.2.0 is published at <https://edfortheblind.github.io/milstrip-guide/>
from public commit `5d77a028ffba99a63e19f51e942d2201eec97566`. GitHub Pages reports
that commit built. Anonymous HTTPS returned 200 and `text/html`; served HTML
matched committed bytes exactly (SHA256
`1613c7135aa4edb075ee650bfdc427a21575d0b7addb8ff42466999165222b6c`).

## Edition 1.3.0 ? September 24, 2026

This update supersedes earlier unpublished-app status. Both apps are published
in the existing MILSTRIP solution. Stage passed Studio runtime checks against
local PostgreSQL. Prod has a separate verified connection and remains disabled
without a target. The actual player presented a licensing prompt; the owner
assigned licensing to IT and declined trial enrollment. Publication does not
establish licensed player acceptance.

The guide contains six operator steps, five current screen captures (including
the native administrator screen), seven diagrams and 970 prose words. The
Results capture was taken after a completed read of the retained Stage request.
An independent editorial pass checked controls, outcomes, current/planned claims
and the licensing distinction. The full guide is 13 pages; the quick SOP is four.
Both PDFs keep the licensing limit on the first page and passed public identifier
and metadata checks.

Isolated browser checks passed for image decoding, dialogs and Escape, internal
anchors, disclosures, print expansion, SVG text bounds, 390/1440-pixel overflow,
no browser errors and no external asset requests. Allowlisted packaging passed.
The backend suite passed 242 tests with two dependency deprecation warnings.
See [runtime delivery evidence](../delivery/RUNTIME_PROFILES_2026-09-24.md).

The public webpage is served from commit
`e9aa07039c2763a23b6ab430745dae82d7561103`. GitHub Pages reports that commit built.
Anonymous HTTPS returned 200 and `text/html`; served bytes match the committed
HTML exactly, and match the source after Git's CRLF-to-LF normalization.
SHA256: `4e7505e60fa3ee82d0f9001c86bc4c596ee718f16c2583b0941efcb21af033cf`.
