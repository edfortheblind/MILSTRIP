# MILSTRIP Intake Automation — Master Document

**Version:** 0.8 **Date:** 2026-08-14 **Status:** PHASE_2A_CODE_ACCEPTED_WINDOWS_GATE

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
Phase 1 has no production writes, but the owner requested a Full independent
audit after the initial implementation. That audit returned FAIL and this
corrective increment incorporates new normative DLM evidence. Future database
design and any production-connected phase use Full/high-risk gates.

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

There are no owner decisions blocking Phase 2A development. Deferred inputs in
`docs/OWNER_QUESTIONNAIRE.md` block the operational 76-field `.txt`, packaging
release, transfer and database phases only.

## 7. Document control

Git history is the change log for this document. A durable, non-obvious
decision gets its own ADR under `docs/adr/` rather than a rewrite of this
file's prose. This document does not itself authorize any production
database change — see the governance profile note in § 2.

## 8. Phase 1 acceptance

Phase 1 is accepted. The exact approvals are preserved once in the decision
history below. This does not authorize later-phase file delivery, database,
credentials, connectivity or production writes.

## 9. Decision history

| Date | Decision | Current effect |
|---|---|---|
| 2026-08-14 | P1-A: deterministic punctuation repair remains `REQUIRES_REVIEW` | Accepted Phase 1 behavior |
| 2026-08-14 | P2-A: AF6 parses but remains `REQUIRES_REVIEW` | Accepted Phase 1 behavior |
| 2026-08-14 | P3-A: preserve observed A2 `SMS` tail and report `INFO` | Accepted Phase 1 behavior |
| 2026-08-14 | P4-A: Phase 1 GO | Phase 1 closed/accepted |
| 2026-08-14 | ADR 0002: future application-owned database required | Phase 3; layout/platform pending |
| 2026-08-14 | ADR 0003: Rainbow file/transfer is intended delivery boundary | Still valid in principle; exact input contract reopened by Shawn's 76-field sample |
| 2026-08-14 | Installable Windows toolkit requested | Phase 2 at APP decision gate |
| 2026-08-14 | Private Chromium extension found feasible | Proposed Phase 4; owner priority pending |
| 2026-08-14 | APP1-A, APP2-B, APP3-A, APP5-A and WEB1-A | Native Windows app; paste/`.txt`; no provisional CSV; Desktop default; extension stays Phase 4 |
| 2026-08-14 | APP4 deferred; Azure/Entra SSO mentioned | Develop without auth/signing; installer trust and any identity requirement move to a later gate |
| 2026-08-14 | Shawn confirmed sample layout and `.txt` extension | Phase 2B target is the 76-field pipe-delimited `.txt`; field-source/edge contracts remain deferred |
| 2026-08-14 | Phase 2A independent code re-audit PASS | Native source accepted; Windows packaging/accessibility/EDR release gate remains open |

Historical decisions belong here or in an ADR. They must not be copied back
into the active questionnaire.

## 10. Documentation ownership

| Document | Owns |
|---|---|
| `master.md` | Status, invariants and decision history |
| `OWNER_QUESTIONNAIRE.md` | Pending owner/business decisions only |
| `ROADMAP.md` | Phase order and exit boundary |
| `MILSTRIP_SPEC.md` | Record contract |
| `RAINBOW_INTERFACE_CONTRACT.md` | Rainbow file/transfer byte contract |
| `ARCHITECTURE.md` | Component and integration boundaries |
| `DISCOVERY_EVIDENCE.md` / `docs/discovery/` | Evidence and interpretation |
| `docs/design/` | Proposed designs awaiting/implementing decisions |
| `docs/adr/` | Durable architecture decisions |
