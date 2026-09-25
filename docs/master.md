# MILSTRIP Intake Automation — Master Document

**Version:** 1.2 **Date:** 2026-09-24 **Status:** PLAYERS_VERIFIED_ADMINISTRATION_BLOCKED_PROD_DISABLED

**Published apps:** Licensing is resolved for the verified player sessions.
MILSTRIP Stage (`7f1b64d0-d51a-4ec8-84ad-2b18fe8c2f82`) passed health and retained
results reads in the actual published player. MILSTRIP Prod
(`0aa02d8b-c7fa-42cc-87e8-6d287bd4c897`) opens in its published player and reports
`Database: DISABLED`. Its independent database target still requires owner approval.
Stage continues to use local PostgreSQL and the existing solution, connector and
gateway. No new Canvas version has been published for the administration work.

**Hosting target confirmed September 25, 2026:** Move the entire MILSTRIP
backend off personal laptops. The API/HTTPS service, all Stage/Prod databases
and gateway runtime belong on always-on, IT-managed servers inside TAB's network.
Power Apps and Power Automate remain Microsoft-hosted. Reuse the existing
solution, connector and gateway registration; relocate the gateway runtime through
the supported migration procedure. The internal API names are
`milstrip.austinlighthouse.org` and `stage-milstrip.austinlighthouse.org`.
IT must assign the service hosts, private IPs and certificates. This is the
deployment target, not a completed migration or database cutover. See the
[network hosting requirements](RUNTIME_CONFIGURATION.md#tab-network-hosting-target).

**Administration rollout:** Both six-screen v2 drafts are saved and natively
exported, with no direct API data source. Independent executable comparison
verified six screens, 81 controls and 679 source properties in each draft. The
four v2 role-display/message-handling fixes are recorded in the
[Canvas evidence](delivery/CANVAS_SOURCE_ASSEMBLY_2026-09-24.md).
Neither administration version is published. The source suite passed **372 tests;
73 database opt-in tests were skipped**, with two upstream dependency warnings
in 77.51 seconds.
The latest pagination/flow/package/sharing batch passed **43 tests**. Skipped tests are not
live database or tenant acceptance.

The existing connector exposes eight operations, including `InvokeBroker`, and
gateway connectivity is verified. Both broker references are bound and both
native flows are **Started**:

- Stage: `04d6229f-5ab8-f111-aaac-7ced8d6f317c`.
- Prod: `fbe87a93-68ef-4efb-88db-facc21c125f6`.

The **Power Automate Management connection is Connected**, using existing TAB
SSO: `MILSTRIPManagementSSO`, ID `07c12ec437fa43e289082155a221a981`. Licensing and
OAuth are resolved; no SSO provider change is required. The
[TAB sysadmin SOP](TAB_SSO_SETUP_SOP.md) records the working procedure, recovery
and two successful native Stage run-metadata checks. Protected inputs/outputs
were verified without opening protected content.

Native Stage checks passed for `GetCurrentUser`, `GetHealth`, `ListUsers`,
`GetRuntimeProfiles`, saving a configuration draft and testing the unchanged
target. Prod passed SSO and administration/configuration reads with its database
disabled. Apply, sharing/recovery and second-user acceptance remain incomplete.
After three executions returned incomplete app readback, the final built-in
pagination trial stalled for more than eight minutes at `Before_add_stage_app`
and was canceled in the native run UI around 23:48 UTC. It reached no permission
mutation or Management call. The command remains pending and its durable lease
remains RUNNING; no Management permit is held. Earlier flow grants remain
verified and neither app CanView grant was added. Stop native retries. The next
step is independent design of canceled-run reconciliation and finite permission
readback; do not clear the lease or fabricate completion. The
[pagination evidence](delivery/MAKERS_PERMISSION_PAGINATION_2026-09-24.md) records
exact recovery references. No OAuth or IT policy change is needed.

Claude and Mike are ACTIVE protected application Owners after readback of their
CanView grants on both apps and run-only grants on both flows. Ed is ACTIVE Admin
and retains platform deployment ownership. Kristen, Thomas and Shawn remain
PENDING. Private control therefore has three active and three pending memberships;
security enforcement and runtime authority remain inactive. The published
four-screen apps still use the shared connection's API identity.

The flows share one durable Management connector permit with a 13-second
cooldown after each confirmed call. Unknown outcomes hold the permit until
recovery. Six serial native calls observed post-completion intervals of at least
13.516 seconds. Concurrent/timeout recovery acceptance remains pending.

The [deployment manifest](../powerapps/canvas/deployment-manifest.json) records
the published apps; [ADR 0006](adr/0006-user-identity-and-administration.md) and the
[implementation contract](delivery/IDENTITY_ADMIN_IMPLEMENTATION_CONTRACT_2026-09-24.md)
define the pending rollout. The [administrator SOP](RUNTIME_CONFIGURATION.md)
covers both configuration authorities and explicit application-schema provisioning.
Active control mode will use one private `control.json`, per-profile request
draining and tested configuration changes. Until that cutover, the legacy private
runtime configuration remains the running authority.

PostgreSQL and SQL Server adapters are implemented; live Azure SQL acceptance is
not established. Shared API releases and restarts affect both apps. The earlier
[runtime/publication evidence](delivery/RUNTIME_PROFILES_2026-09-24.md) records the
242-test increment and its then-current licensing limitation; it is historical.

Use the [visual operating package](operations-guide/index.html) for the functional
flow, architecture, end-user SOP and evidence limits.
The earlier [Phase 2 plan](operations-guide/guide.md#phase-2-two-production-periods)
assumed existing Azure SQL first, then accepted production PostgreSQL with an
end-Q4 2026 target. Its hosting assumption is superseded by the September 25
requirement that all target databases reside on internal TAB VMs. SQL Server and
PostgreSQL support remains relevant; engine/version, migration sequencing and
Stage/Prod placement still require confirmation. Historical guide material is
not approval for an Azure-hosted target or a database cutover.
Earlier increment sections are historical snapshots. The public visual guide
**1.4.0** is published and verified; it describes the current four-screen release
and clearly leaves administration acceptance pending. This status supplies the
more detailed implementation and blocker evidence.

The September 23 [acknowledgement update](delivery/ACKNOWLEDGEMENT_DESIGN_2026-09-23.md)
added the persistent intake receipt now included in Stage. The
[retained September 24 runtime test](delivery/RETAINED_RUNTIME_TEST_2026-09-24.md)
preserves its intake, reviews and audit events in PostgreSQL. Do not delete it.
Production handoff and downstream receipts remain Phase 2 work; the current API
still records the shared connection identity on the published app path.
The illustrated guide has a separate editorial review and publication standard.
Incoming change documents belong in the local [inbox](../inbox/README.md).

Built with the AEKR (AI Engineering Knowledge Repo) workflow — see the root
`README.md` footer and `meta/OPERATING_PRINCIPLES.md` in the `AEKR` repo for
what that means. This document is this project's own single source of truth;
it does not duplicate that framework's content, only points at it.

## 0. Normative scope

This document binds the MILSTRIP intake automation project specifically. The
detailed field specification lives in `docs/MILSTRIP_SPEC.md` (normative for
the record format), architecture and the deferred integration decisions in
`docs/ARCHITECTURE.md` and `docs/adr/`, and the phased plan in
`docs/ROADMAP.md`. Durable decisions get an ADR under `docs/adr/`. Ed Lopez
(HOC) is the approval authority for scope changes, per the AEKR constitution
this project's `CLAUDE.md` / `AGENTS.md` carries.

## 1. What this is

Shawn Hinkle (Travis 3PL) manually repairs and formats urgent MILSTRIP orders
that arrive by email/Freshservice ticket before hand-typing them into a SQL
staging script. This project automates that specific, painful step — parsing
inconsistent human input into a correctly-formed 80-character MILSTRIP record
— without touching the stable pipeline downstream of it (`download_ship940`
→ ADF → `ShipMaster` → Boomi → SCALE). It is explicitly **not** a rebuild or
redesign of that downstream pipeline, the legacy 3PL database, or SCALE.

## 2. Governance profile

**Lean for normal Phase 1 operation; Full for the current corrective gate.**
Phase 1 was accepted after the August corrective audit. The September backend
corrections have implementation verification recorded in
`docs/delivery/BACKEND_CORRECTION_2026-09-23.md`; they have not received a new
independent Audit. The Full-profile orchestration-loop and definition-of-done
files referenced by the constitution are absent. Future database design and
any production-connected phase use Full/high-risk gates.

## 3. Confirmed scope of Phase 1 (accepted 2026-08-14)

**In:** extract raw pasted email/ticket text → conservative transport
normalization → family-aware structural + semantic validation → lossless
canonical 80-character MILSTRIP → human-readable/JSON report.
CLI + Windows `.bat` launcher. Zero database access. Zero network access.
Zero writes anywhere.

**Explicitly out (see `docs/ROADMAP.md` for when/if each returns):**
database validation (NSN/DODAAC lookups), submission to
`staging_download_shipMILS`, generic positional shift repair, Freshservice API intake, any web
or Power Apps UI.

## 4. Core domain model

See `docs/MILSTRIP_SPEC.md` and `docs/DISCOVERY_EVIDENCE.md`. Implemented in
`milstrip/domain.py::FIELD_SPECS` — that module and this spec must change
together.

## 5. System invariants

1. Nothing in Phase 1 ever writes to a database or the network.
2. A field value is never silently invented or auto-corrected without a
   deterministic rule backed by real evidence (see `MILSTRIP_SPEC.md` §
   Deterministic repair).
3. The canonical record is exactly 80 printable ASCII characters and preserves
   every received position; input over 80 is rejected, never truncated.
4. `milstrip/domain.py::FIELD_SPECS` is the positional source for parsing. The
   canonical builder preserves the validated normalized source line directly
   and only right-pads, preventing reconstruction from discarding data.
5. Application-facing deliverables, operator instructions, runtime messages
   and final interface contracts are written in English. Discovery evidence
   and internal research notes may remain in their source language.

## 6. Outstanding decisions and gates

- Phase 2 will create the final Rainbow CSV and deliver it through the vendor's
  FTP boundary. The CSV layout and connectivity contracts are pending; no
  serializer or network adapter is authorized yet. See ADR 0003.
- Application-owned persistence is implemented locally in PostgreSQL's
  `milstrip_app` schema under ADR 0004. Final hosting, identity and production
  connection design remain pending; ADR 0002 records the original requirement.
- Local development is now authorized against the owner's localhost PostgreSQL
  instance. The local migration may create only standalone objects inside the
  `milstrip_app` schema; it must not alter existing operational objects. See
  ADR 0004 and `docs/POSTGRESQL_HOSTING_DESIGN.md`.
- The local database review confirmed the migrated legacy MILSTRIP and 940
  tables already exist under `dbo`. The new `milstrip_app` tables are metadata
  for intake/review/audit, not copies of legacy business tables. The original
  raw-MILS SQL contract has been recovered. The approved temporary-table
  handoff test passed; independent review and operational acceptance remain
  pending. See
  `docs/MILSTRIP_LEGACY_FLOW_REVIEW.md`.
- The live SQL Server source remains authoritative while PostgreSQL is a future
  deployment target. PostgreSQL is not approved for cutover, dual-write or SQL
  decommissioning until controlled parity and the raw-MILS handoff contract are
  proven.
- The agreed migration route is documented in
  `docs/PSQL_INTELLIGENCE_ROADMAP.md`: develop PostgreSQL intelligence and new
  capabilities first, run a controlled two-month dry run with SQL still live,
  then migrate ownership and archive/decommission SQL only after approval.
- All ten items in `docs/OPEN_QUESTIONS.md` — none block Phase 1; several
  block specific later phases as noted there.
- Repository license/confidentiality classification (`OPEN_QUESTIONS.md` Q10)
  — a proprietary/internal default is in place pending Ed's confirmation.

## 7. Document control

Git history is the change log for this document. A durable, non-obvious
decision gets its own ADR under `docs/adr/` rather than a rewrite of this
file's prose. This document does not itself authorize any production
database change — see the governance profile note in § 2.

## 8. Phase 1 acceptance

Following the Full corrective audit, Ed Lopez approved P1-A, P2-A, P3-A and
P4-A on 2026-08-14. This accepts the local parser behavior and closes the
Phase 1 owner gate. It does not authorize Phase 2 CSV creation/delivery,
Rainbow production delivery, legacy table writes, or production database
changes. A local development database slice is separately authorized under
the `milstrip_app` isolation boundary. No legacy-table write is authorized
until the original parser/handoff contract is recovered and approved.

## 9. Current backend increment

The parser, local intake API, metadata migrations, pure PostgreSQL parser and
read-only legacy row mapper are present. The original one-case/six-field parity
check has been expanded to 18 cases and all 14 exposed SQL fields. Input stock
values retain all 15 positions; the 13-character legacy projection is blocked
when positions 21-22 are populated. Duplicate classification now uses ERP order
across all DICs. The test suite includes real PostgreSQL persistence and rollback
checks. Exact execution and deployment evidence is in the correction report.

The owner approved the synthetic temporary-table handoff test on 2026-09-23.
All 38 mapped columns, duplicate checks, rollback and retry passed; the temporary
target was removed. The owner subsequently accepted the backend ("all good
with the backend"), authorized commit/push and requested implementation
preparation. The next local increment is prepared in
`docs/delivery/IMPLEMENTATION_PLAN.md`: operator review API contracts, request
and record reads, then auditable review decisions and Power Apps preparation.
This owner acceptance is not an independent Audit result. Operational legacy
writes, shared frontend rollout and SQL Server retirement retain their separate
contracts and acceptance gates.

## 10. Operator API increment

The owner approved implementation of the prepared plan. Request listing,
record/issue detail, versioned/idempotent local review commands and scoped audit
history are implemented. Migration 005 is installed locally. The suite passes
139 tests, including real two-session review conflict verification; installed
parser parity and live loopback HTTP checks pass. See
`docs/delivery/OPERATOR_API_IMPLEMENTATION_2026-09-23.md` for evidence and
`docs/OPERATOR_API_CONTRACT.md` for the API and Power Apps preparation contract.

Local review identity is explicitly configured and is not shared-user
authentication. Power Platform environment access, an approved API path and
identity/role mapping are the next connected-integration inputs.

## 11. Laptop-first Power Apps development setup

The successful procedure is now [PowerApps setup](../sop/powerapps-setup.md).
See the [conversation record](../sop/conversation-record.md) for decisions and
the [restart prompt](../restart-prompt.md) to continue in a separate session.

Current setup (2026-09-23): the owner used the existing organization Default
environment, created the MILSTRIP solution and MILSTRIP Local Dev API connector,
and registered the standard MILSTRIP-DEV-LAPTOP gateway. GetHealth returned
HTTP 200 through the gateway after correcting HTTPS to HTTP for loopback port
8000. The tested process exposes health only; Basic authentication enforcement
and application routes through the connector remain pending. The connector
export is in `powerapps/connectors/`; the supplied app icon is in `assets/`.
The pre-commit verification passed all 139 tests with the local database enabled
and confirmed the backend OpenAPI artifact matches the runtime schema.

The owner confirmed the laptop remains the development backend host. The
setup and handoff procedure is `docs/POWER_APPS_LAPTOP_DEV_SOP.md`: create/select
a Power Platform Developer workspace, register a standard gateway on the same
laptop and authenticate the local PAC CLI. This establishes prerequisites for
the agent to implement connector authentication and the development app.
The SOP describes the original setup recommendation; the existing Default
environment was used instead of creating a Developer environment. No cloud
API/database host is required at this stage. Power Apps
connector creation also needs an OpenAPI 2.0 artifact; the existing 3.1 export
remains the runtime API reference.

## 12. Authenticated connector increment

Dedicated Basic authentication now protects all seven `/api/v1` operations.
Intake/review audit identity comes from the authenticated username, replacing
the unauthenticated local-reviewer setting. All application calls enforce the
approved loopback/database boundary. Private credential setup stores a salted
verifier in the Git-ignored `.cred` folder; the repeatable launcher preserves the gateway path.

The existing connector artifact now exposes typed intake, listing, details,
results, review and history. Four canvas control sets are prepared locally.
The owner supplied saved app ID `7f1b64d0-d51a-4ec8-84ad-2b18fe8c2f82`;
solution membership and Studio execution remain unverified. Reuse this app.
The existing gateway service is installed/running; authenticated tenant tooling
is unavailable in this session. The owner completed private credential setup;
the authenticated API replaced the temporary health-only process on port 8000.
Live missing/invalid credential checks return 401. The owner verified local
authentication with HTTP 200, then supplied a screenshot of GetHealth returning
200 through the existing gateway after selecting a replacement connection with
the matching private credential. The owner subsequently saved the updated
connector and supplied a Test-tab screenshot showing all seven operations.
The one-command standalone API/database workflow passed with synthetic cleanup;
see `sop/standalone-workflow-test.md`. The owner requested moving on to canvas
implementation rather than more individual Swagger tests. Application operations
through Power Platform will be checked during canvas integration.

Follow [the continuation SOP](../sop/local-api-development.md) and
`powerapps/canvas/README.md`. Local verification is not an independent Audit
or shared-app rollout acceptance. No operational legacy writes are authorized.

## Canvas execution update (2026-09-23)

The existing app now contains the four implemented screens and a saved unpublished
draft. Live gateway integration passed the synthetic intake/results/review/history
path. See [canvas execution evidence](delivery/CANVAS_IMPLEMENTATION_2026-09-23.md)
for the remaining acceptance boundary. No independent Audit is claimed.
