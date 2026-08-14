# ADR 0001 — Defer the new-database strategy decision past Phase 1

**Status:** SUPERSEDED IN PART BY ADR 0002
**Date:** 2026-08-14

## Context

The originating local-only design brief (`local-discovery/AEKR Full Design
Master Prompt — MILSTRIP Automation - Lean Audit Version.md`, § 6) asks for
an early decision between
four database options (new Azure SQL, new PostgreSQL, extracted legacy
objects, or no new database) via a comparison ADR. Ed's own note when
requesting that brief already flagged PostgreSQL only as a *maybe*, not a
decision. On the 2026-08-12 call, Ed asked Shawn whether this process's data
could live in a separate database from the main 3PL one; Shawn's answer was
"possibly," while pointing out that a lot of the existing schema is shared
static reference data he deliberately avoided duplicating ("I didn't want to
hard code stuff... I wanted to be able to use this stuff elsewhere").

Phase 1 (this delivery) is a pure text-parsing CLI: extract, normalize,
structurally/semantically validate, and rebuild a canonical MILSTRIP record.
It reads no database and writes no database.

## Decision

> **2026-08-14 update:** ADR 0002 resolves that a new application-owned
> database will exist. This ADR remains controlling only for deferral of
> platform, schema, connectivity and migration details until the supplied
> layout and real contracts are reviewed.

Do not decide the database strategy now. Phase 1 ships with zero database
dependency. The decision is revisited when Phase 2 (read-only `ItemMaster` /
`cfg_dodaac_active` validation) is actually designed, with real query-pattern
evidence from Phase 1's pilot use instead of a speculative comparison.

## Alternatives considered

Deciding now, per the original brief's Option A-D framework, using only
today's evidence. Rejected: none of the four options can be meaningfully
compared yet without knowing Phase 2's actual read volume/latency needs and
Phase 3's actual write/idempotency needs — exactly the kind of premature
architecture `meta/OPERATING_PRINCIPLES.md` (imported from AEKR) warns
against. A rushed choice here would also preempt Shawn's legitimate "possibly"
— he has direct operational knowledge of which parts of his schema are safe
to leave alone versus worth carving out, and that conversation has not
happened yet.

## Consequences

Phase 3's design work must start with that database-strategy conversation
(with Shawn, using the questions in `OPEN_QUESTIONS.md` Q4 as a starting
point) before writing any read-access code. ADR 0002 closes the "no new
database" option; platform, schema, connectivity and migration choices remain
open. Phase 1 requires no migration because it never touched a database.
