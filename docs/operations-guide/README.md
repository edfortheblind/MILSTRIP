# MILSTRIP operator guide — edition 1.3.0

**Share:** [MILSTRIP operator guide](https://edfortheblind.github.io/milstrip-guide/).
The webpage opens without a download or login. App access is separate.

This edition adds Stage/Prod administration and the native database configuration
screen. Stage and Prod were published on September 24 in the existing solution.
Stage passed Studio tests against local PostgreSQL. Published-player access is
blocked by the current account's Power Apps license prompt; no trial was accepted.
Prod's separate profile remains disabled pending an independent target. Azure SQL runtime
acceptance, production handoff and downstream receipts remain outstanding.

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
| [Current architecture](diagrams/02-current-architecture.svg) | Credential-bound Stage/Prod profiles, shared API and configurable targets |
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
