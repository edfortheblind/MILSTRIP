# Next Session Prompt

Continue the MILSTRIP backend migration from the completed local parity gate.

## Current state

- PostgreSQL 18.6 local target: `trav3pl-psqldb-stage` on `localhost:5432`.
- SQL Server remains authoritative and must not be decommissioned yet.
- The owner-run SQL was recovered in `inbox/MILSTRIP helper NewMultiple_Protoype 1.sql`.
- Correct legacy flow: raw `staging_download_shipMILS` -> direct `download_ship940` insert.
- `staging_download_ship940` is not part of the MILSTRIP owner-run path.
- `milstrip_app` stores new intake, parser results, validation issues, review and audit metadata.
- Python parser and PostgreSQL parser parity passed.
- Full Python suite: 47 passed.
- Read-only handoff dry run passed duplicate protection for `SL470162240DCV`.
- No legacy write has been enabled.

## Next gate

Design and execute a controlled non-duplicate PostgreSQL legacy handoff test.

Requirements:

1. Use an owner-approved synthetic/test MILSTRIP record.
2. Confirm NSN exists in `dbo.ItemMaster` and effective DODAAC in
   `dbo.cfg_dodaac_active`.
3. Insert only into a disposable or explicitly approved PostgreSQL legacy test
   target, never the live SQL Server database.
4. Verify the mapped `download_ship940` row and all required legacy fields.
5. Verify rollback and duplicate behavior.
6. Keep SQL Server operational and unchanged.

Do not start Power Apps/frontend work until this backend handoff contract is
approved. Do not decommission SQL Server or introduce dual writes.
