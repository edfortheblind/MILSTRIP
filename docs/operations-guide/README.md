# MILSTRIP operations and Phase 2 package

**Prepared September 23, 2026. Current facts and proposed future states are labeled separately.**

- [Open the offline visual guide](index.html) — all seven charts, operating instructions, architecture and Phase 2 plan. No web service or CDN is required.
- [Download / print the PDF](MILSTRIP-current-and-phase2.pdf).
- [Read the editable source](guide.md) — evidence references and detailed plan.

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
```

The builder uses the existing local Brave executable in an **isolated headless
process**. It does not reuse the signed-in browser session or access the tenant.
Supply `--browser <absolute chromium executable path>` if necessary. Omit
`--pdf` to build HTML/SVG without a browser. Edit `guide.md` for text and
`scripts/build_operations_guide.py` for chart content/layout; generated files
should not be manually edited.

Validation checks all seven SVGs, rendered node/text bounds, HTML section links,
browser errors and desktop/mobile overflow. PDF layout is also inspected after
generation. These documentation checks are not app UAT or an independent Audit.
No application code, production database, tenant resource or shared Git history
is changed by the build.

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
