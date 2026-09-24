# MILSTRIP Intake Automation

Automates the painful part of Travis 3PL's urgent MILSTRIP order intake: turning
inconsistent, copy-pasted email/Freshservice text into a correctly-formed
80-character MILSTRIP record — without touching the stable pipeline downstream
of it (`download_ship940` → ADF → `ShipMaster` → Boomi → SCALE).

## Status

**2026-09-24: MILSTRIP Stage and Prod published; player licensing remains with IT.**
Stage retains app ID `7f1b64d0-d51a-4ec8-84ad-2b18fe8c2f82`. The separate Prod app
is `0aa02d8b-c7fa-42cc-87e8-6d287bd4c897`; its separate connection is verified, and
its runtime profile is disabled while the database target is undecided. Both are
in the existing MILSTRIP solution and reuse its connector and gateway.

The standalone Prod player requested a Power Apps plan for the current account.
The owner assigned licensing to IT; no trial was started. Studio Preview checks
passed, but end-user player acceptance remains blocked until licensing is resolved.

API **0.4.0** binds separate API credentials to fixed Stage/Prod profiles and
checks the database's environment identity. Stage uses local PostgreSQL;
PostgreSQL and SQL Server persistence adapters are implemented. Live Azure SQL
acceptance remains pending. Configure destinations privately through the
[administrator screen and SOP](docs/RUNTIME_CONFIGURATION.md).

Synthetic intake, review, receipt and history have passed through the existing
app. The retained runtime test remains in Stage; see
[its evidence and read-only query](docs/delivery/RETAINED_RUNTIME_TEST_2026-09-24.md).
Audit identity is still the shared API account. Remaining canvas acceptance and
individual-user authorization are separate work.

Start with the [visual operating guide](docs/operations-guide/index.html) or
[PDF](docs/operations-guide/MILSTRIP-current-and-phase2.pdf): current functional
flow, technical architecture, user SOP and the proposed Phase 2 periods
(existing Azure SQL, then production PostgreSQL by the end-Q4 target).
Production delivery/cutover remain gated. See [`docs/master.md`](docs/master.md)
for status and [`docs/ROADMAP.md`](docs/ROADMAP.md) for historical phase context.

**Share with anyone:** [read the guide online](https://edfortheblind.github.io/milstrip-guide/).
The SOP, diagrams and Phase 2 plan open directly in a browser. No download or
login is needed. Reading the guide does not grant access to the Power App.

## Quick start

Requires Python 3.10+, nothing else — the Phase 1 toolkit has zero
third-party dependencies.

```bash
# Windows: drag a .txt file with the raw request onto run_milstrip.bat, or:
run_milstrip.bat request.txt

# Any platform, from a terminal:
python -m milstrip.cli request.txt
python -m milstrip.cli request.txt --json
type request.txt | python -m milstrip.cli   # or: cat request.txt | python -m milstrip.cli
```

After cloning onto Windows, run the included smoke test:

```bat
run_milstrip.bat samples\known_valid.txt
```

The CLI commands above are Phase 1 dry runs — no CSV is created, nothing is written
to a database and nothing is sent over the network. The canvas app does persist
intake and review metadata through the API. `--json` is a developer
diagnostic report, not the Rainbow deliverable. The future operational output
is CSV; its format will not be invented before the official layout arrives.

For complete operator instructions, result interpretation, exit codes and
failure handling, see [`docs/USER_SOP.md`](docs/USER_SOP.md).

## Documentation

- [`docs/master.md`](docs/master.md) — single source of truth: scope,
  governance profile, status, outstanding decisions.
- [`docs/RUNTIME_CONFIGURATION.md`](docs/RUNTIME_CONFIGURATION.md) — native
  administrator setup, explicit schema provisioning, restart and database moves.
- [`powerapps/canvas/deployment-manifest.json`](powerapps/canvas/deployment-manifest.json)
  — Stage/Prod app IDs, source variants and deployment status.
- [`docs/MILSTRIP_SPEC.md`](docs/MILSTRIP_SPEC.md) — the fixed-width field
  specification, with evidence and confidence levels for every position.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — current-state and target
  diagrams, system boundary, legacy integration classification.
- [`docs/RAINBOW_INTERFACE_CONTRACT.md`](docs/RAINBOW_INTERFACE_CONTRACT.md) —
  Phase 2 CSV/transfer contract template, open fields and acceptance evidence.
- [`docs/DISCOVERY_EVIDENCE.md`](docs/DISCOVERY_EVIDENCE.md) — source-to-claim
  register for SQL, calls, DLM appendices and sanitized malformed-email facts.
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — current production plan and historical
  phase decisions; SQL versus Rainbow handoff remains unresolved.
- [`docs/OPEN_QUESTIONS.md`](docs/OPEN_QUESTIONS.md) — ten precise questions,
  each tagged with which phase it blocks.
- [`docs/OWNER_QUESTIONNAIRE.md`](docs/OWNER_QUESTIONNAIRE.md) — owner
  decisions for Rainbow CSV/FTP and the future application database.
- [`docs/USER_SOP.md`](docs/USER_SOP.md) — English operator SOP with the
  current Phase 1 procedure and planned Rainbow CSV/FTP procedure.
- [`api/README.md`](api/README.md) — local API reference; the current Stage/Prod
  configuration procedure is in the administrator SOP above.
- [`db/migrations/001_create_milstrip_app.sql`](db/migrations/001_create_milstrip_app.sql)
  — isolated local development schema migration; no legacy table writes.
- [`docs/POSTGRESQL_HOSTING_DESIGN.md`](docs/POSTGRESQL_HOSTING_DESIGN.md) —
  future TAB-network and Azure VM hosting placeholders.
- [`docs/MILSTRIP_LEGACY_FLOW_REVIEW.md`](docs/MILSTRIP_LEGACY_FLOW_REVIEW.md) —
  read-only review of the existing MILSTRIP/940 tables and corrective backend
  handoff map.
- [`docs/PSQL_INTELLIGENCE_ROADMAP.md`](docs/PSQL_INTELLIGENCE_ROADMAP.md) —
  agreed PostgreSQL development, dry-run, cutover and SQL retirement route.
- [`docs/delivery/FINAL_AUDIT.md`](docs/delivery/FINAL_AUDIT.md) — Full focused
  audit evidence, verdict and remaining security gate.
- [`docs/adr/`](docs/adr/) — durable architectural decisions.
- [`PROJECT_MAP.md`](PROJECT_MAP.md) / [`PROJECT_MAP.html`](PROJECT_MAP.html)
  — visual overview of how the pieces fit together.
- `local-discovery/` — optional local-only raw evidence, intentionally ignored
  by Git and never included in the GitHub deliverable.

## Running the tests

```bash
pip install -r requirements-dev.txt
python -m pytest -v
```

The suite covers parser regressions, API authentication, runtime profiles and
persistence contracts. Database integration checks require an explicitly
configured test target; they are not live Azure SQL acceptance. Use the current
delivery evidence for executed test results rather than a historical test count.

## Project layout

```text
milstrip/            Phase 1 Python package (domain, intake, parsing, validation, canonical, cli)
tests/                Tests + real-example fixtures
run_milstrip.bat       Windows launcher
docs/                 Design documentation (this project's own)
local-discovery/       Local-only raw evidence; ignored by Git and not distributed
CLAUDE.md / AGENTS.md  AEKR engineering constitution (governance)
OWNER_PROFILE.md       Owner calibration (Ed Lopez, HOC)
```

## License

Proprietary — see [`LICENSE`](LICENSE). This repository handles DLA/military
logistics operational data and is not open source.

---

Built with the **AI Engineering Knowledge Repo (AEKR)** workflow.

![Build with AEKR](assets/aekr-banner.png)
