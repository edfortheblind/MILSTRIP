# Retained application runtime test

**Status: DONE.** Executed September 24, 2026, 09:54–09:56 America/Chicago.
The owner requested a complete current runtime test with database records kept.
No cleanup or deletion was performed.

## Route and result

Existing MILSTRIP Intake Dev in Studio Preview → existing custom connector and
gateway → running authenticated FastAPI service → local PostgreSQL
`localhost:5432/trav3pl-psqldb-stage`, schema `milstrip_app`.

Request: `1d0c784d-c3bf-495c-928c-0b66687a58a4`.
Source ID: `fced0c15-e938-4b00-832a-73b9e214166e`.
Synthetic run marker: `eaf57c78-7a16-47ab-b591-969fce2c4c9a`.

| Record | Validation | Canonical length | Saved review | Version |
|---|---|---:|---|---:|
| 1 | VALID | 80 | APPROVED | 1 |
| 2 | REJECTED | NULL | REJECTED | 1 |

The synthetic fixture uses fictitious requisition `ZZ999926700001` plus an
intentionally incomplete `A2A` candidate. Record 2 reports `MIL-STR-002` and the
app disables approval for it. Both reviews were entered and saved through the
app, with reasons explicitly identifying retained test evidence.

The saved receipt, refreshed results, both review confirmations and all three
history events were observed in the app. PostgreSQL retains **1 intake, 2
records, 1 validation issue, 2 reviews and 3 audit events** (event IDs 22–24).
An independent agent confirmed those rows using a read-only transaction.
The audit actor is the shared development identity `milstrip-app`.

The intake's validation status remains REJECTED because one candidate is invalid.
Review decisions are separate from validation; approval does not change that
status. The current runtime ends at review and audit. Production stored-procedure
execution, CSV transfer and downstream/Boomi acknowledgement remain disconnected.

## Inspect the retained data

Use [the read-only query](../../db/queries/retained_runtime_2026-09-24.sql) in
the database above. It returns final results, validation issues and audit events
in three result sets. No sample operational table was written, no app formula
was changed, and no app publication was performed for this test.

App-only capture evidence remains outside Git under
`%LOCALAPPDATA%\MILSTRIP\ui\retained-*.png`; the run manifest is
`retained-runtime-20260924.json` in that directory.

**Retention:** keep this request and its related rows until the owner explicitly
requests removal. Do not include it in cleanup for subsequent synthetic tests.
