# MILSTRIP operator guide — web edition 1.2.0

**Evidence date: September 23, 2026.** Current development behavior and proposed production work remain separate.

**Share this webpage:** [MILSTRIP operator guide](https://edfortheblind.github.io/milstrip-guide/).
It opens directly in a browser, with no download or login. This publishes documentation, not the Power App.

- [Open the offline visual guide](index.html) — all seven charts, operating instructions, architecture and Phase 2 plan. No web service or CDN is required.
- [Read the 12-page illustrated PDF](MILSTRIP-current-and-phase2.pdf).
- [Print the four-page illustrated SOP](MILSTRIP-quick-sop.pdf).
- [Edit the public guide](guide.md), [styles](theme.css) or [interactions](guide.js).
- [Read the internal engineering notes](engineering-notes.md) for the complete implementation plan, evidence and gates. These notes are excluded from the public release.
- [Acknowledgement design](../delivery/ACKNOWLEDGEMENT_DESIGN_2026-09-23.md) distinguishes the implemented intake receipt from proposed production handoff and downstream receipt.
- [Editorial standard](EDITORIAL_STANDARD.md) defines the writing and peer-review requirements for future editions.

| Chart | Status | Standalone file |
|---|---|---|
| Functional flow | Current development app and separate existing manual production path | [SVG](diagrams/01-current-functional.svg) |
| Technical architecture | Current cloud connector / laptop API / local PostgreSQL | [SVG](diagrams/02-current-architecture.svg) |
| End-user SOP | Current controls, decisions and exception paths | [SVG](diagrams/03-current-user-sop.svg) |
| P2.1 architecture | Proposed published app using existing Azure SQL | [SVG](diagrams/04-phase2-azure-sql.svg) |
| Phase 2 release flow | Proposed eligibility, command, handoff and acknowledgement | [SVG](diagrams/05-phase2-functional.svg) |
| P2.2 architecture | Proposed PostgreSQL production after migration acceptance | [SVG](diagrams/06-phase2-postgresql.svg) |
| Transition roadmap | Proposed two-period timing, qualification and rollback windows | [SVG](diagrams/07-phase2-transition.svg) |

The current app is saved **unpublished**. Publication is an explicit assumption
for Phase 2, not a current fact. The PostgreSQL production target is end of Q4
2026, subject to migration and operational acceptance. SQL retirement has a
separate stabilization/approval gate and may extend into January 2027.

## Rebuild

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m pip install -r docs\operations-guide\requirements.txt
.\.venv\Scripts\python.exe scripts\build_operations_guide.py --pdf
.\.venv\Scripts\python.exe scripts\package_operations_guide.py --output-dir "$env:LOCALAPPDATA\MILSTRIP\release-v1.2.0"
```

The builder uses the existing local Brave executable in an **isolated headless
process**. It does not reuse the signed-in browser session or access the tenant.
Supply `--browser <absolute chromium executable path>` if necessary. Omit
`--pdf` to build HTML/SVG without a browser. Edit `guide.md` for text and
`scripts/build_operations_guide.py` for chart content/layout. The HTML embeds CSS,
JavaScript, the icon, four real app screenshots and every SVG, including downloadable diagram copies.
Generated files should not be manually edited.

Validation checks a lone HTML file in an isolated directory, four screenshots, seven SVGs, six SOP
steps, rendered text bounds, section links, disclosures, keyboard dialog closing,
print expansion, browser errors, no network dependencies and desktop/mobile
overflow. The public packager uses an explicit allowlist, checks identifiers and
offline links, and creates a deterministic ZIP plus SHA256 checksums. PDF text
and layout are checked separately. See [verification](VERIFICATION.md) and the
[independent editorial review](EDITORIAL_REVIEW.md).

The public repository hosts the standalone `index.html` through GitHub Pages
from the root of `main`, with `.nojekyll`. The webpage is the primary deliverable;
the earlier release assets remain optional archives. The source repository stays private.
No runtime code, production database or tenant resource is changed by these tools.

Screenshots sit beside their corresponding SOP steps and open at full size.
See [capture provenance](screens/README.md). The current webpage is edition 1.2.0;
the previously published 1.1.0 download release is retained unchanged as an archive.

This edition replaces repeated status cards and explanatory prose with six
operator steps, recovery disclosures and a short confirmation table. The Results
screen now retains the saved intake receipt while the operator refreshes results
or reviews a record. All four screenshots were recaptured from the saved draft.

## Production design items requiring decisions

1. Reconcile the migration repo's recorded SQL freeze with the requested Azure
   SQL operating period and refresh the final migration baseline as necessary.
2. Accept one delivery route: the recovered SQL boundary or the older Rainbow
   CSV/FTP proposal. Database hosting alone does not choose that route.
3. Approve individual-user authorization, API/network hosting, workload/recovery
   targets, final migration scope and the writer cutover plan.

The package is complete as a documentation/design deliverable. Those decisions
gate later production implementation; they are explicitly identified rather than
represented as completed work.
