# Open Questions

Kept short on purpose — 10 precise questions, not a 50-item interview.
Nothing here blocks the corrected Phase 1 parser; each question states which
future phase it blocks.

## Q1 — How must Rainbow CSV represent positions 67-80? — BLOCKING Phase 2A
Resolved normatively: A2 and A5_/AF6 have different DLM tails. Still open:
Travis A2 evidence carries the legacy `SMS` variant at 67-69, and the current
SQL ignores or hardcodes parts of the tail. The Rainbow layout and accepted
sample must show whether the CSV carries the complete 80-character record or
maps these values to separate columns.

## Q2 — More garbled/misaligned examples — NON-BLOCKING, BLOCKING for generic repair
The 2026-08-14 PDF supplies the first concrete punctuation-compression case.
One record has a unique, auditable repair; the 14-digit identifier has no safe
repair and is rejected. More real anomalies are still required before adding
generic shift or spacing rules.

## Q3 — `staging_download_shipMILS` is marked `SENT` unconditionally — DOWNSTREAM OBSERVATION
The existing SQL sets `milsStatus = 'SENT'` after the insert attempt
regardless of whether the conditional `INSERT ... SELECT` actually produced a
row (e.g. unknown NSN, duplicate order). A MILSTRIP can end up marked `SENT`
without ever reaching `download_ship940`. This is existing, untouched
production logic — not something this project changes — but Phase 3
(Injector) should design an honest status pipeline
(`RECEIVED → PARSED → VALIDATED → STAGED → 940_CREATED → ERROR`) instead of
inheriting the same ambiguity. Under ADR 0003, this application does not write
that table directly; Rainbow owns the downstream transition.

## Q4 — New database layout and connection contract — BLOCKING before Phase 3 design
ADR 0002 resolves that a new application database will exist. Awaiting the
owner-supplied table layout. Still needed: ownership/retention rules, expected
volume, platform choice, environments, restricted identities, network path,
and the exact read/write contract with legacy Azure SQL.

## Q5 — Which Stock/Part Number variants occur at Travis? — NON-BLOCKING
DLM resolves that 8-22 is a 15-position Stock or Part Number field and that
72-73 are family-defined data, not gaps. Collect examples of part numbers,
subsistence type-of-pack and populated management fields before reference
validation is finalized.

## Q6 — Definition of "duplicate" — BLOCKING Phase 2 delivery design
Same `ERP_ORDER`? Same ticket + MILSTRIP text? Is intentional resubmission
(correcting a prior error) a real workflow that needs a distinct path from an
accidental duplicate?

## Q7 — Which DIC variants are supported by Rainbow? — BLOCKING Phase 2A
DLM includes A2_, A5_ and AF6. Phase 1 parses those layout groups; AF6 is held
for review because its end-to-end behavior through the current SQL is not
verified. Confirm exact third characters and AF6 handling for the legacy
write contract.

## Q8 — Legacy A2 `SMS` placement — BLOCKING Phase 2A
AP8.25 defines 67-69 as date of receipt, but Travis A2 traffic places `SMS`
there. Confirm whether submission must preserve that operational variant or
transform to the normative A2 tail at the controlled boundary.

## Q9 — Realistic Freshservice ticket export samples — NON-BLOCKING for Phase 1, BLOCKING for Phase 4 (ticket intake)
The original design brief expected Freshservice screenshots as evidence; none
were present in this repo. Needed before building an adapter that reads
directly from a ticket instead of a pasted text file.

## Q10 — Repository license / confidentiality classification
This repo touches DLA/military logistics operational data. `docs/master.md`
and the repo `LICENSE` currently assume "internal/proprietary, all rights
reserved" as a default, following AEKR's own guidance to treat client/work
repos as proprietary unless genuinely meant to be open. Confirm that's
correct, or state the actual policy (e.g. employer-owned, specific
confidentiality marking) so it can be recorded precisely instead of assumed.
