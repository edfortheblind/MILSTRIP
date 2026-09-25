# Roadmap

**Current September 25 roadmap:** [TAB hosting, in-app configuration and intake controls](delivery/INTAKE_NETWORK_ROADMAP_2026-09-25.md). Keep local development now; deploy the API/gateway to TAB-managed hosts after IT confirms names. Existing Azure SQL Stage/Prod precede PostgreSQL.

**Planning update (2026-09-23):** the owner requested a new production Phase 2
with publication assumed: **P2.1 existing Azure SQL**, then **P2.2 production
PostgreSQL**, targeting end of Q4 2026 after the migration project is fully live.
The complete [two-period plan](operations-guide/guide.md#phase-2-two-production-periods)
includes capacity, migration scope, freeze reconciliation, release gates and
rollback. These period labels are separate from the older CSV/FTP 2A/2B labels
below. The delivery-route decision remains explicit; no live deployment or write
is authorized by preparing this plan.

Current implementation update (2026-09-23): the local PostgreSQL application
schema and intake API now exist, and the owner accepted the corrected backend.
Use `docs/PSQL_INTELLIGENCE_ROADMAP.md` for the migration route and
`docs/delivery/IMPLEMENTATION_PLAN.md` for the next local API slice. The phase
ordering below records the original delivery plan; its Phase 3 "not started"
description is historical. The Rainbow delivery contract still requires an
explicit decision before any alternative operational writer is implemented.

Scaled down from the original design brief's 9-sprint plan to match what's
actually been discovered and built so far. Each phase only gets designed in
detail once the phase before it is real and in use — see AEKR's own
`17_anti_patterns/deterministic-does-not-mean-unsupervised.md` and
`meta/OPERATING_PRINCIPLES.md` (*"never recommend complexity for its own
sake"*). Nothing below Phase 1 is designed in detail yet.

## Phase 1 — Parser (ACCEPTED 2026-08-14)

Python CLI + `.bat` launcher. Extracts candidate lines while preserving HTML
record boundaries, applies evidence-backed transport cleanup, parses
family-aware fixed-width fields, validates them, and builds a lossless
80-character canonical record. It has zero database/network access. Exit codes
distinguish success, rejected records and intake failure.

**Current evidence:** canonical output is deterministic and lossless; >80,
Unicode, zero-candidate, DODAAC and HTML multi-record failures have regression
tests. The PDF's unique spacing repair remains human-review; its invalid
14-digit identifier is blocked without guessing. 46 tests pass and mypy is
clean. The focused Full audit passed with observations and Ed approved
P1-A/P2-A/P3-A/P4-A on 2026-08-14.

## Phase 1.5 — Additional deterministic repair (NOT STARTED)

Extend beyond the one punctuation-compression pattern now evidenced and built.
Generic shifts remain blocked on Q2: every rule needs real examples and a
unique valid interpretation.

## Phase 2 — Rainbow CSV delivery (PLANNED; CONTRACTS PENDING)

The application will turn eligible canonical records into the authoritative
Rainbow CSV format and deliver the resulting file to Rainbow's FTP endpoint,
where the established process takes over. ADR 0003 makes this the target
handoff and supersedes the earlier plan for a direct staging-table injector.

Phase 2 is intentionally split:

- **2A — CSV contract + local export:** implement only after receiving the
  exact layout, accepted sample, filename/batch rules and operator eligibility
  policy. The `.bat` launcher will then create the final CSV as its last local
  step.
- **2B — FTP transport + delivery evidence:** implement only after receiving
  the actual protocol, endpoint, paths, authentication, secret-management,
  retry, duplicate and acknowledgement contracts. Local creation and remote
  delivery are separate observable states.

Phase 2 uses Full/high-risk gates because malformed or duplicate outbound files
can affect production. It requires golden-file tests, a safe non-production
transfer test, an independent Audit and explicit owner GO. Until then, the
current `.bat` remains Phase 1 parser-only and does not create or upload CSVs.

## Phase 3 — Application database + reference validation (NOT STARTED)

Design and create the new application-owned database approved in ADR 0002,
then add application state, traceability and the approved reference-validation
contracts. No schema or connection is implemented until the owner supplies the
table layout and database questionnaire answers. The database must not become
a prerequisite for Phase 2 unless a later approved design establishes that
need. This phase uses Full/high-risk gates.

## Phase 4 — Ticket intake (NOT STARTED)

Read directly from a Freshservice ticket (API or export) instead of a
manually pasted text file. Blocked on Q9 — no real ticket export samples
collected yet.

## Phase 5 — Operations "last mile" (NOT STARTED, explicitly deferred by Ed)

A form/button for Operations to run this without Shawn or Ed present —
Shawn's stated North Star. Ed, 2026-08-14: *"No veamos ahora una solución
web... sí aceptaría un toolkit local."* Power Apps was floated on the call as
the likely delivery mechanism, using the existing Power Apps service account
Shawn already provisioned. Not designed until Phases 1-4 are in real use.

## What "done" means for this pipeline, end to end

Under ADR 0003, this toolkit's eventual responsibility ends when the exact
Rainbow CSV has been transferred and the agreed delivery-success condition is
observed. A local file write alone is not delivery. Rainbow and the normal
existing process own all subsequent processing. The precise acknowledgement
that closes the handoff is pending the Phase 2 connectivity contract.
