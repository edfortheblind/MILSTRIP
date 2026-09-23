# Next Session Prompt

Continue from the 2026-09-23 backend correction evidence in
`docs/delivery/BACKEND_CORRECTION_2026-09-23.md`.

Latest increment: `docs/delivery/OPERATOR_API_IMPLEMENTATION_2026-09-23.md`.
The approved local operator API is implemented; use
`docs/OPERATOR_API_CONTRACT.md` and `docs/operator-api.openapi.json` as its contract.

The owner requested laptop-first Power Apps setup. Follow
`docs/POWER_APPS_LAPTOP_DEV_SOP.md` and read
`local-discovery/powerapps-dev-handoff.md` when supplied. The API/PostgreSQL remain
on the laptop; the cloud Developer environment holds Power Apps components.
Next: verify PAC/solution/gateway access, implement dedicated gateway-compatible
API authentication and produce an OpenAPI 2.0 connector. The existing OpenAPI 3.1
export is reference material, not the connector import artifact.

## Current state

- PostgreSQL 18.6 local target: `trav3pl-psqldb-stage` on `localhost:5432`.
- SQL Server remains authoritative and must not be decommissioned yet.
- The owner-run SQL was recovered in `inbox/MILSTRIP helper NewMultiple_Protoype 1.sql`.
- Correct legacy flow: raw `staging_download_shipMILS` -> direct `download_ship940` insert.
- `staging_download_ship940` is not part of the MILSTRIP owner-run path.
- `milstrip_app` stores new intake, parser results, validation issues, review and audit metadata.
- Migration 004 is installed locally. Parser parity passed 18 cases and all
  14 exposed PostgreSQL fields; SQL extraction is not semantic validation.
- Migration 005 adds review versions, command IDs and supporting indexes.
- Full suite with local database tests enabled: 139 passed, including HTTP
  behavior and two-session review conflict checks.
- Validation rejects malformed DICs, blank stock and non-ASCII/control input.
- Fifteen-character input stock values are preserved; legacy mapping blocks
  populated positions 21-22 instead of truncating them.
- Read-only handoff dry run passed duplicate protection for `SL470162240DCV`.
- The owner-approved temporary-table handoff passed all 38 mapped fields,
  duplicate checks across DICs, rollback and retry. The temporary target was
  removed; the synthetic order remained absent from the operational table.
- No legacy write has been enabled.

## Next implementation

Power Apps setup has since progressed: the owner created the MILSTRIP solution
in the existing organization Default environment, registered the standard
MILSTRIP-DEV-LAPTOP gateway, and verified GetHealth through the connector with
HTTP 200. The gateway must call HTTP, not HTTPS, on loopback port 8000.
The unchanged OpenAPI 2.0 connector export is at
`powerapps/connectors/MILSTRIP-Local-Dev-API.swagger.json`; the app icon is
`assets/milstrip-app.png`. Only a temporary health-only process was exposed for
this test. It does not enforce Basic authentication or expose application routes.
Next: implement dedicated local API authentication and server-derived reviewer
identity, extend the connector operations, then build the canvas screens.
PAC authentication and automated tenant access have not been verified. Do not
recreate the existing environment, solution or gateway. Logs and credentials
remain outside Git.

The owner accepted the backend and approved the subsequent implementation.
All four interfaces in `docs/delivery/IMPLEMENTATION_PLAN.md` are implemented
locally: request list, record details, review decisions and audit history.
Continue connected Power Apps integration from the setup recorded above;
identity/role mapping remains to be implemented. No new independent
Audit has been performed; implementation tests must not be described as one.

## Repeatable handoff evidence

The owner approved the following fixture and temporary target on
2026-09-23, and the controlled test passed:
NSN `8405016819440`, DODAAC `SC0141`, quantity `1`, synthetic requisition
`ZZ999926600001`. The target is `pg_temp.milstrip_handoff_test`; all writes roll
back and the temporary table is removed. Run
`.venv/Scripts/python.exe scripts/run_controlled_handoff_test.py --execute`
to repeat the same approved experiment. Running without `--execute` repeats
read-only preparation. Approval persists for this fixture and temporary target;
no additional approval is needed to repeat the same test.

Completed experiment requirements:

1. Use an owner-approved synthetic/test MILSTRIP record.
2. Confirm NSN exists in `dbo.ItemMaster` and effective DODAAC in
   `dbo.cfg_dodaac_active`.
3. Insert only into a disposable or explicitly approved PostgreSQL legacy test
   target, never the live SQL Server database.
4. Verify the mapped `download_ship940` row and all required legacy fields.
5. Verify rollback and duplicate behavior.
6. Keep SQL Server operational and unchanged.

The historical August audit does not
cover this implementation. A future writer needs separately approved atomic
duplicate/retry and staging/SENT semantics; the current mapper performs no
operational writes. Commit and push are authorized for the corrected backend
and implementation-preparation documents.

Power Apps preparation may proceed against the accepted local contract;
automated environment access and identity are still needed for shared implementation.
Resolve the Rainbow-versus-legacy delivery boundary before operational writes.
Do not decommission SQL Server or introduce dual writes.
