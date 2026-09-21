# ADR 0003 — Rainbow CSV/FTP is the delivery boundary

**Status:** Accepted in principle — 2026-08-14

**Decision owner:** Ed Lopez (HOC)

## Context

Phase 1 produces validated 80-character canonical MILSTRIP records but does
not create an outbound file or use the network. Earlier planning assumed a
future direct insert into `staging_download_shipMILS`. The owner has now
clarified the intended operational handoff: the Windows launcher must
eventually create a CSV file and the application must be able to place that
file on Rainbow's FTP endpoint, where the established process will pick it up.

The exact CSV layout, filename convention, batching rules, FTP protocol,
endpoint, authentication, directories and acknowledgement behavior are not
yet available. Inventing any of those details could create a file that looks
successful while being rejected, duplicated or misrouted downstream.

## Decision

Phase 2 owns the outbound Rainbow handoff and is split into two controlled
increments:

1. **Phase 2A — CSV contract and local export.** Once the owner supplies the
   authoritative layout, implement a deterministic serializer that writes the
   exact required CSV to a local output directory. Only eligible records may
   be exported. The parser and CSV serializer remain separate components.
2. **Phase 2B — Rainbow FTP delivery.** Once connectivity and security details
   are supplied, add a replaceable transport adapter that transfers an already
   validated CSV, verifies the configured success condition and retains an
   auditable local result. Network delivery is never inferred merely from a
   successful local file write.

The Windows `.bat` launcher will orchestrate parsing, review gating and CSV
creation only after Phase 2A is implemented and accepted. FTP upload must be
an explicit, separately observable operation; whether it is automatic after
CSV creation or requires operator confirmation remains an owner decision.

Direct writes to `staging_download_shipMILS` are removed from the target
architecture unless later evidence establishes them as an independent
requirement. Rainbow and the existing process own everything after the
verified FTP handoff.

The new application database remains required under ADR 0002, but its design
and implementation move to Phase 3. Phase 2 must not depend on that database:
local manifests and structured results may provide interim traceability
without pre-empting the future schema.

## Required contracts before implementation

- one authoritative CSV specification and at least one accepted sample;
- filename, extension, encoding, delimiter, quoting, line-ending, header,
  trailer and batch rules;
- eligibility policy for `VALID` and `REQUIRES_REVIEW` records;
- output-directory and collision/overwrite policy;
- actual transfer protocol (FTP, FTPS or SFTP), host/port and remote paths;
- authentication and secret-storage approach per environment;
- atomic-upload, retry, timeout, duplicate and acknowledgement behavior;
- DEV/TEST endpoint or a safe vendor-approved test procedure.

## Consequences

- Phase 1 remains accepted and unchanged: no file export and no network use.
- Phase 2 cannot be called implemented until its contract is supplied, tested
  against golden files and independently audited.
- A locally created CSV and a remotely delivered CSV are distinct states.
- No credentials, production endpoint or client data may be committed.
- ADR 0002 remains valid, with its implementation phase changed from Phase 2
  to Phase 3.
