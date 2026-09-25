# Edition 1.6.0 — September 25, 2026

**Independent final editorial review and guide publication verification passed.** Stage 16 and Prod 6 are Live for limited acceptance.
Native acceptance for bindings, memberships, broker-only host authority,
existing-target Configuration, intake completion, duplicate blocking and override
is recorded in the separate
[pilot acceptance note](../delivery/NATIVE_PILOT_ACCEPTANCE_2026-09-25.md).

The isolated browser build passed standalone offline loading, six operator steps,
four app reference captures plus one historical host-editor capture, seven charts,
image decoding, anchors, disclosures, enlargement, Escape dismissal, print
expansion, SVG text bounds and 390/1440-pixel overflow checks. It made no HTTP
requests and reported no browser errors. The signed-in browser was not used.

Author measurements from rendered `main` text, excluding SVG text and figure
controls, are **943 reading words** and **455 visible words** with disclosures
closed. The operator and overview sections contain **294 visible words**.
Headings, table cells, captions and disclosure summaries are included. The
counting expression is `\b[\w]+(?:[-’'][\w]+)*\b`.

The full PDF has **13 pages**; the quick SOP has **four**. Both passed extracted
text and metadata privacy checks and retain version 1.6.0, limited-acceptance
status, source-ID intake recovery and same-command review retry. Public Markdown
passed the private-identifier guard. The allowlisted package contains five
release assets plus SHA256SUMS.txt, with seven standalone SVGs in its deterministic
ZIP. No screenshots were added or modified. The seven chart word counts, in
filename order, are 133, 167, 195, 163, 158, 164 and 181.

These checks verify documentation artifacts. They do not establish second-user,
role or intake-submission recovery acceptance, Azure SQL readiness or delivery.
The separate final reviewer confirmed exact artifact hashes, word/image/chart
counts, rendered preview and architecture layout, public privacy/offline guards,
the exact 11-member ZIP allowlist, checksums, source-byte equality and unchanged
embedded reference images. No must-fix editorial finding remained. The deployed HTML comparison is recorded below.

Public commit `17173e137e1270361b037327a06bf2b3d79055ac` was pushed to the
existing guide repository. Pages reported **built** at **20:35:16 UTC**.
Anonymous HTTP at the canonical guide URL returned HTTP200 and **2,158,022 bytes**
at **20:36:19 UTC**, exactly equal to `HEAD:index.html` from that public commit:
SHA-256 `a44e71fe5c7344c38b59fd714cdfc563fd09bd8199d78e89c388e3faddb7fa39`.
Git normalized exactly 279 CRLF line endings to LF when staging HTML. A byte
comparison proved this was the only difference from the reviewed frozen local
HTML below; the source and offline package retain their original frozen bytes.
The initial HTTP read during Pages building still returned edition 1.5 and was
not treated as successful verification. A separate reviewer repeated the anonymous
HTTP, Git blob, newline-equivalence, remote-head and Pages-build checks and
independently confirmed publication.

Frozen at **20:32:32 UTC**, SHA-256:

- HTML: `18be78c7bef3a4b6cff3db53c85301dd69620424f915360316437d1cd5bae1d1`
- Full PDF: `2425efab6d49db517b8b331d3f9883567e2910547efad851d4a49db3ef199745`
- Quick SOP: `08589c48ded397225876598ec1e7615c05e8ef5bd9634fa881a5b485cb6a5a84`
- ZIP: `3d1dbeb1028eaa5b39e62418af6888c07ef9cdc0b86354afceb5ae7ebdddc9cf`

Earlier records below apply to their named editions.

---

# Web edition 1.5.0 — September 25, 2026

Published at [the existing guide URL](https://edfortheblind.github.io/milstrip-guide/)
from public commit `0c54fdc0e2d6779954ed799974ad7eccd4fe5afa`.
Anonymous HTTPS returned 200 and its 2,156,505-byte body exactly matched the
committed `index.html`, SHA-256
`1edc851bb7f33a5433fee3683d14c82ef56a4fc42c4e3a317bae5a9942072136`.

The separate [editorial review](EDITORIAL_REVIEW.md) passed at 994 reading words,
328 visible operator/overview words, six steps, five screenshots and seven charts.
The isolated browser build passed offline loading, disclosures, enlargement,
Escape dismissal, anchors, print expansion, text bounds and 390/1440-pixel layouts.
The 13-page full PDF and four-page quick SOP passed version/date, extracted-text
and metadata checks. The public package allowlist and private-identifier guards
passed. The public repository receives only HTML, README and safe verification
text; private reports, configuration and native app exports are excluded.

This release describes September 25 saved drafts and the hosting roadmap while
retaining September 24 player evidence. It does not publish the updated apps or
enable access enforcement. Earlier edition evidence below is historical.

---

# Web edition 1.4.0 — September 24, 2026

Published at [the existing guide URL](https://edfortheblind.github.io/milstrip-guide/).
GitHub Pages built public commit `af9334de8eec8d81afc945489a3e5ee9515b1613`
on September 24 at 23:32:24 UTC. Anonymous HTTP returned 200, and its
2,156,601-byte response exactly matched the committed `index.html`:
`95352cb6c39537c559dc26d30762b174e0eb28d3b49ac4f0127ea62ad74f4dcb`.

The local browser/PDF checks are recorded in [publicverification.md](publicverification.md).
The public package was independently checked for private configuration, tokens,
tenant/app IDs and personal email addresses. Existing synthetic screenshots remain;
the History capture retains the service audit name, not an authentication secret.
This publication updates documentation; it does not publish the new app drafts or
activate user enforcement. Earlier release evidence below is historical.

---

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

## Edition 1.4.0 — local verification, publication pending

Licensing was verified for the current administrator. Stage passed connection and saved-results checks in the
published player; Prod opens with its database disabled. The existing Studio
captures are unchanged. Corporate SSO connections are configured, but
individual-user enforcement and the implemented administration screens await
native deployment acceptance. No live SSO enforcement is claimed.

The reading edition was reduced from 1,137 to **1,000 words**; its closed-detail
view contains **473 words**. Six operator steps and recovery distinctions remain.
The administrator section separates the current host procedure from pending
in-app administration. README and screenshot provenance now reflect this status.
The root agent's independent final editorial review remains pending.

`build_operations_guide.py --pdf` and `package_operations_guide.py` passed. The
isolated browser verified five decoded images, seven charts, six steps, internal
anchors, enlargement/Escape, disclosure controls, print expansion, SVG text
bounds, and no overflow at 390/1440 pixels. No external asset requests or browser
errors occurred. The 13-page guide and four-page SOP passed extracted-text,
metadata, link and page-boundary checks. Visual inspection covered all four SOP
pages and the current/pending administration page.

The public package uses the existing explicit allowlist. A separate public
verification note contains no internal user names, resource IDs or source links.
Local HTML SHA256:
`2c775e8edeeac4789c330b9dae33bbd7b66fe80fa670a6dedb3bf3d934bcff7b`.
Copying verified files into the public checkout does not publish them; no commit,
push or Pages deployment was performed during this verification.
