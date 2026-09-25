# MILSTRIP Intake Automation - Master Document

**Version:** 1.4 **Date:** 2026-09-25 **Status:** PILOT_PUBLISHED_MULTIUSER_ACCEPTANCE_PENDING_PROD_DISABLED

The owner resumed the September 25 release cut and authorized publication of both
existing apps and the operating guide, plus commit/push. The current release uses
the existing solution, gateway, connector, two apps and two broker flows. See the
[native pilot evidence](delivery/NATIVE_PILOT_ACCEPTANCE_2026-09-25.md) and
[pilot publication order](delivery/PILOT_PUBLISH_ORDER_2026-09-25.md). The earlier
[release cut](delivery/RELEASE_CUT_2026-09-25.md) is a historical checkpoint.

**Current runtime and access:** All six configured memberships are ACTIVE, each
with a completed current sharing plan. Existing protected Owners and deployment
ownership are preserved. All sharing executions are closed; no sharing lease or
Management permit is outstanding. Broker-only security enforcement and runtime
authority were activated at 19:24:13 UTC and the API restarted. Direct shared
Basic access is denied before credential verification. One private control store
now owns membership, configuration and audit state; the legacy runtime file is
preserved but is no longer the active configuration authority. Do not restore the
old direct-access bypass.

Both updated broker flows are On. Independent native export comparison matched
each trigger and all 417 actions, with expected connection serialization changes.
Office 365 Users supplies the run-only caller's identity; API and sharing
connections remain private. The bounded protected permission reader passed a
native trial for both apps (two pages, three cumulative rows each); its diagnostic
is Off. See [permission evidence](delivery/NATIVE_PERMISSION_VALIDATION_2026-09-25.md)
and [design](delivery/FINITE_PERMISSION_READ_DESIGN_2026-09-25.md).

**Canvas publication:** Stage version **16** and Prod version **6** are Live
(Power Apps release 3.26091.11) for the existing six-person audience. Both matching
broker bindings were saved and exported. The apps retain 85 controls, 724 source
properties, 37 behavior handlers, six screen events and three App properties;
all 4,367 executable rules were unchanged by binding refresh. Studio reported
zero formula errors. Export diagnostics retain one Parser, zero Binding, two
literal-predicate SARIF findings and 66 accessibility items per app; these baseline
items are not claimed resolved. The [actual deployment manifest](../powerapps/canvas/deployment-manifest.json)
records the live versions. Stage's updated standalone player is Ready; its Configuration load, retained
request reopening and audit-history read passed. Prod's updated player also passed administration and Configuration reads while its
database remained disabled. Its first post-consent startup stalled; one read-only
reload completed startup. The initial stall's cause is unproven.

**Native acceptance:** Both drafts resolve the current administrator through TAB
SSO. Stage reports Ready against the retained local PostgreSQL target. Prod's
database remains disabled while its administration works. In Stage Configuration,
Save/Test/Apply passed for the unchanged target, including an unexpired matching
test receipt, missing-test rejection, enabled-target Initialize guard and actual
uncertain-command recovery. Only Stage's profile revision changed; Prod and the
connection targets were unchanged. No database initialization occurred.

Two synthetic two-record intakes now have all four final decisions, one decision
and audit per record, with no active workflow remaining. A real uncertain review
response recovered with the same command without another decision/version change.
Unfinished review blocked submission even with an administrator override reason.
After final decisions, Resume / new intake cleared the form. A CRLF/terminal-newline
variant was blocked as the same normalized intake within two hours, with no added
receipt. A blank override reason blocked Submit; an explicit reason created one
distinct intake and one override audit linking the original receipt and human
actor. Both override records were then reviewed. Historical rows were preserved.

Intake-specific unknown-submission recovery, actual second-user identity,
role/denied-user, revocation and concurrent-session acceptance remain open.
Licensing is verified only for the administrator's actual sessions, not all six
recipients. Limited publication does not establish full multi-user acceptance.

**Requirements and hosting:** Power Apps and Power Automate remain Microsoft-hosted.
The API/HTTPS service and gateway will move to always-on IT-managed hosts inside
TAB's network once hostnames and infrastructure are ready. The initial database
targets will be existing Azure SQL Stage and Prod; PostgreSQL follows after
separate schema/data migration acceptance. The app detects the provider from its
connection string. Admin/Owner-only Configuration supplies Save, Test, Apply and
explicit Initialize actions in Power Apps. A connection-string change does not
migrate data or remove target-readiness checks. No Azure SQL connection, DNS change,
operational SQL Server write or production cutover has been performed.

Every record needs a final review before the operator starts another intake.
Identical normalized content is blocked across users for two hours within an
environment. Admin/Owner can override duplicates with an audited reason, but
cannot bypass unfinished review. The [network roadmap](delivery/INTAKE_NETWORK_ROADMAP_2026-09-25.md),
[administrator SOP](RUNTIME_CONFIGURATION.md), [TAB SSO SOP](TAB_SSO_SETUP_SOP.md)
and [ADR 0006](adr/0006-user-identity-and-administration.md) describe the design
and remaining deployment inputs. Local PostgreSQL schema version 2 and retained
acceptance rows remain in place. Delivery to the operational pipeline is not connected.

**Verification and guide:** Source commit `925478e` passed **1,003 tests, none
skipped**, with two upstream warnings. Reader/flow/package checks and separate
reviews are recorded in the delivery evidence. Earlier test counts and native
snapshots in linked documents describe preceding states, not current blockers.
Guide **1.6.0** is live at https://edfortheblind.github.io/milstrip-guide/.
Public commit `17173e1` passed independent editorial review and Pages deployment;
anonymous HTTP returned the exact committed HTML. Git normalized only line endings
from the reviewed local build. Its publication is separate from app publication. The [visual operating package](operations-guide/index.html)
retains the Azure SQL-first then PostgreSQL roadmap and explicit acceptance limits.

Historical retained runtime and recovery records must not be deleted or replayed.
The canceled historical sharing execution was recovered and its lease closed;
old noncurrent pending plans do not invalidate completed current memberships.
Incoming change documents belong in the local [inbox](../inbox/README.md).

Built with the AEKR workflow; see the root README and the AEKR repository's
`meta/OPERATING_PRINCIPLES.md`. This is the project's source of truth; it references
that framework without duplicating it.

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

## 9. Historical backend increment

Sections 9-12 and the dated Canvas update preserve September 23 checkpoints.
Their current/next/pending wording refers to those increments; the September 25
status at the top of this document is the active deployment record.

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
