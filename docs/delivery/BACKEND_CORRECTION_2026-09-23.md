# Backend correction and verification — 2026-09-23

Status: corrections and temporary-table handoff verified; backend accepted by owner.

The owner subsequently stated "all good with the backend" and explicitly
authorized commit/push and preparation for implementation. The next increment
is documented in `IMPLEMENTATION_PLAN.md`. This is owner acceptance, not a
claim that an independent Audit was performed.

## Scope and contract

This increment corrects deterministic validation, parser parity, duplicate
classification and application persistence. It prepares an isolated legacy
handoff experiment. SQL Server remains authoritative. There is no production
write endpoint, cutover, dual write, frontend or Rainbow delivery change.

The input stock/part field is positions 8-22 (15 characters), preserved by both
Python and PostgreSQL. The legacy SQL uses positions 8-20 (13 characters).
The mapper accepts this projection only when positions 21-22 are blank. A
populated extension blocks handoff for review; no truncation, invented lookup
or business reinterpretation is authorized. The SQL parsing function performs
positional extraction and transport checks, not Python's semantic validation.

The final anti-join in the recovered owner-run SQL rejects an ERP order across
all DIC values. Dry-run classification now applies that rule, including
trailing-space equivalence. A read-only duplicate check is not a concurrent
idempotency guarantee: a future writer still needs an approved atomic contract.

The mapper blocks rejected and review-required records, including A5E address
exceptions, AF6, unobserved DIC variants and M quantities. Resolving those
business cases is outside this increment.

## Verification plan and evidence

- Thirteen new validation regressions failed on the original code, then passed
  after fixes. Cases cover DIC, blank stock, control/Unicode characters,
  overlength trailing spaces and embedded HTML-like contamination.
- PostgreSQL tests compare all 14 exposed fields over 18 cases: A2, A5, A5E,
  AF6, lowercase, suffixes, both DODAAC branches, 15-character parts, M quantity
  and minimum-length records. Transport failure cases are tested separately.
- API handler integration tests use real PostgreSQL transactions for request,
  record, issue and audit persistence; aggregate status; repaired/raw values;
  missing requests; database/configuration errors; and late-write rollback.
  These are handler tests, not HTTP transport/authentication acceptance.
- Migrations 001-004 are exercised inside force-rollback transactions. Identity
  sequences are transactionally restarted for test allocation so subsequent
  runs restore their prior state. No application test rows are retained.
- Complete synthetic row expectations check every mapped field against the
  recovered SQL, including reference-derived unit and price.
- Final enabled-database suite: **106 passed**. The installed-function read-only
  parity script passed **18 cases x 14 fields**. The existing legacy order dry
  run returned **DUPLICATE**, with no legacy write. `git diff --check` passed.
- Default suite without database opt-in: **72 passed, 34 explicitly skipped**.
  Python compilation checks passed. Development dependencies are captured in
  `requirements-dev.txt`.

Reproduce the database suite using the approved local connection string in
`MILSTRIP_TEST_DATABASE_URL`, then run `.venv/Scripts/python.exe -m pytest -q`.
Without that environment variable, database cases are explicitly skipped.
Migration 004 was also applied permanently to the authorized local
`milstrip_app` schema, with all 18 parity cases checked before committing the
database transaction. Installed-function parity was then verified read-only.

## Controlled handoff experiment

Executed script: `scripts/run_controlled_handoff_test.py --execute`.

On 2026-09-23 the owner approved the prepared fixture and temporary target
("all approved, proceed"). Execution passed:

```json
{"mapped_fields":38,"duplicate":"PASS","rollback":"PASS","retry":"PASS","erp_order":"ZZ999926600001","target":"pg_temp.milstrip_handoff_test","legacy_write":false}
```

All 38 mapped columns matched the inserted temporary row. Repeated insertion
and a different DIC with the same ERP order were blocked by the sequential test
guard. Savepoint rollback removed the row, retry succeeded, and outer rollback
removed the temporary table. No operational table was written. The read-only
preparation check was repeated afterward to confirm the synthetic ERP order
remained absent from `dbo.download_ship940`.

- Synthetic requisition: `ZZ999926600001`; DIC `A2A`; quantity `1`.
- Existing lookup keys: NSN `8405016819440`, DODAAC `SC0141`.
- Read-only preparation confirmed exactly one matching item and address and no
  existing ERP order. No address details are stored in the repository/report.
- Fixed target: `pg_temp.milstrip_handoff_test`, cloned from the local legacy
  table's columns, constraints, indexes and identity definitions. Operational
  rows, triggers and foreign keys are not copied. Temporary identity allocation
  cannot advance the operational table's sequence.
- Execution checks all mapped columns, duplicate classification across DICs,
  savepoint rollback and retry, then rolls back the outer transaction and
  confirms the temporary target is gone.

Default execution is read-only preparation. `--execute` is reserved for the
owner-approved fixture/temporary-target test. This is an isolated schema and
mapping check, not downstream operational acceptance or concurrency proof.

## Remaining gates

- The approved synthetic temporary-table test is complete and the owner has
  accepted the local backend for implementation preparation. Operational writer
  contracts and production acceptance remain separate.
- Migration 004 is installed only on the authorized localhost development
  database; no shared deployment was performed. Source-control commit/push is
  now explicitly authorized by the owner.
- The historical `FINAL_AUDIT.md` predates this baseline and does not certify
  these changes. This report is implementation self-verification, not an
  independent Audit. The Full-profile orchestration-loop and definition-of-done
  files referenced by the constitution are absent. Owner acceptance of the
  local baseline is recorded above; independent review has not been performed.
- Full legacy behavior, staging/SENT status semantics, A5E review, retries under
  concurrency and downstream parity remain future acceptance work.
