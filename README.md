# MILSTRIP Intake Automation

Automates the painful part of Travis 3PL's urgent MILSTRIP order intake: turning
inconsistent, copy-pasted email/Freshservice text into a correctly-formed
80-character MILSTRIP record — without touching the stable pipeline downstream
of it (`download_ship940` → ADF → `ShipMaster` → Boomi → SCALE).

## Status

**Phase 1 accepted; Phase 2 planned** — the current release is a local parsing
CLI with zero database/network access. Phase 2 will create the final Rainbow
CSV and deliver it to Rainbow's FTP endpoint after its layout and connectivity
contracts are supplied. The application database is now Phase 3. See
[`docs/master.md`](docs/master.md) for current status and
[`docs/ROADMAP.md`](docs/ROADMAP.md) for what comes next.

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

Every current run is a Phase 1 dry run — no CSV is created, nothing is written
to a database and nothing is sent over the network. `--json` is a developer
diagnostic report, not the Rainbow deliverable. The future operational output
is CSV; its format will not be invented before the official layout arrives.

For complete operator instructions, result interpretation, exit codes and
failure handling, see [`docs/USER_SOP.md`](docs/USER_SOP.md).

## Documentation

- [`docs/master.md`](docs/master.md) — single source of truth: scope,
  governance profile, status, outstanding decisions.
- [`docs/MILSTRIP_SPEC.md`](docs/MILSTRIP_SPEC.md) — the fixed-width field
  specification, with evidence and confidence levels for every position.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — current-state and target
  diagrams, system boundary, legacy integration classification.
- [`docs/RAINBOW_INTERFACE_CONTRACT.md`](docs/RAINBOW_INTERFACE_CONTRACT.md) —
  Phase 2 CSV/transfer contract template, open fields and acceptance evidence.
- [`docs/DISCOVERY_EVIDENCE.md`](docs/DISCOVERY_EVIDENCE.md) — source-to-claim
  register for SQL, calls, DLM appendices and sanitized malformed-email facts.
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — phased plan (Phase 1 accepted, Rainbow
  CSV/FTP in Phase 2, application database in Phase 3).
- [`docs/OPEN_QUESTIONS.md`](docs/OPEN_QUESTIONS.md) — ten precise questions,
  each tagged with which phase it blocks.
- [`docs/OWNER_QUESTIONNAIRE.md`](docs/OWNER_QUESTIONNAIRE.md) — owner
  decisions for Rainbow CSV/FTP and the future application database.
- [`docs/USER_SOP.md`](docs/USER_SOP.md) — English operator SOP with the
  current Phase 1 procedure and planned Rainbow CSV/FTP procedure.
- [`api/README.md`](api/README.md) — local Windows API scope and setup for the
  application-owned PostgreSQL boundary.
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
pip install pytest
python -m pytest -v
```

46 passing, including legacy examples and sanitized regressions derived from
the malformed-email evidence. Static type checking is clean.

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
