# MILSTRIP operator guide — edition 1.6.0

**Share:** [MILSTRIP operator guide](https://edfortheblind.github.io/milstrip-guide/).
The webpage opens without a download or login. App access is separate.

**Evidence edition: September 25, 2026.** Stage version 16 and Prod version 6 are
Live for limited acceptance by the existing six-person audience. Both players
and licensing are verified for the current administrator only. Six memberships,
native bindings and broker-only host authority are active with one API worker.
Configuration Save/Test/Apply, intake completion, normalized duplicate blocking,
audited override and configuration/user-access/review recovery passed. Stage
retains local PostgreSQL; Prod's database stays disabled. Its initial startup
stalled after consent and recovered after one read-only reload; cause is unproven.
Second-user, role, intake-submission recovery and diagnostic/accessibility gates
remain open. Guide publication is recorded by Pages deployment history.

The six operator steps now include every-record completion, normalized two-hour
duplicates, the audited Admin/Owner override and source-ID reconciliation. The
administration section uses the in-app Configuration and Users controls. Five
September 24 reference captures are retained and dated; the host editor image is
explicitly historical. Managed hostnames, Azure SQL runtime, production handoff
and downstream receipts remain unaccepted.

- [Guide source](guide.md), [styles](theme.css), [interactions](guide.js).
- [Full app and database SOP](../../sop/powerapps-setup.md).
- [Database configuration reference](../RUNTIME_CONFIGURATION.md).
- [Engineering notes](engineering-notes.md) and [acknowledgement design](../delivery/ACKNOWLEDGEMENT_DESIGN_2026-09-23.md).
- [Editorial standard](EDITORIAL_STANDARD.md), [verification](VERIFICATION.md) and [screenshot provenance](screens/README.md).
- [Incoming change documents](../../inbox/README.md).

Internal references are not included in the public repository. Its standalone
`index.html` contains the operating instructions, screenshots and seven charts;
the earlier downloadable release remains an optional archive.

| Chart | Scope |
|---|---|
| [Functional flow](diagrams/01-current-functional.svg) | Intake/review and the separate manual production process |
| [Current architecture](diagrams/02-current-architecture.svg) | Fixed Stage/Prod profiles, shared API and configurable targets |
| [Operator procedure](diagrams/03-current-user-sop.svg) | Six steps and recovery branches |
| [Azure SQL](diagrams/04-phase2-azure-sql.svg) | Proposed production hosting and adapter qualification |
| [Release and acknowledgement](diagrams/05-phase2-functional.svg) | Proposed controlled handoff and receiver receipt |
| [PostgreSQL](diagrams/06-phase2-postgresql.svg) | VM/database transition after migration acceptance |
| [Transition schedule](diagrams/07-phase2-transition.svg) | Qualification, cutover and stabilization |

## Rebuild and review

```powershell
.\.venv\Scripts\python.exe -m pip install -r docs\operations-guide\requirements.txt
.\.venv\Scripts\python.exe scripts\build_operations_guide.py
```

Add `--pdf` only when generating the optional full guide and quick SOP. Browser
validation uses an isolated headless Brave process, never the signed-in session.
Use `--browser <absolute chromium path>` to select another installed executable.

Edit `guide.md` for prose and `scripts/build_operations_guide.py` for chart content.
Generated HTML/SVG files must be rebuilt. The output embeds its assets and makes
no network requests. Validation covers six steps, images, seven charts, internal
anchors, disclosures, enlargement dialogs, keyboard dismissal, print expansion
and desktop/mobile overflow.

Follow the editorial standard and obtain a separate factual/editorial review
before publication. Confirm visible controls, current status, screenshot dates
and unknown-outcome recovery. New administration material belongs in a closed
section; the six operator steps remain the main reading path.

GitHub Pages serves the public repository's root `index.html` on `main` with
`.nojekyll`. Publishing this guide does not publish the canvas app or activate a
database configuration. Confirm the deployed page matches the committed HTML.

## Pending production acceptance

Resolve the SQL freeze and approve new application objects before Azure SQL
writes. Accept one delivery contract, individual authorization, hosting,
recovery targets and the migration scope. Changing a connection string does not
transfer existing history. Both apps share API releases and outages.

The PostgreSQL production target remains end of Q4 2026, subject to migration
acceptance. SQL retirement requires separate approval after stabilization.
