# Rainbow CSV and Transfer Contract

**Status:** 76-field pipe layout and `.txt` extension confirmed; field/source
and byte edge-case contract pending

**Phase:** 2A (CSV) and 2B (transfer)
**Do not implement from this template alone.** Every `TBD` requires an
authoritative answer or accepted sample.

## 1. CSV contract — Phase 2B

Shawn confirmed the supplied six-row artifact as the file layout and `.txt` as
the operational extension. It is headerless, pipe-delimited and has 76 fields
per row. Serialization remains blocked because enriched fields are not
derivable from MILSTRIP and their names/sources are still undefined. See
`docs/discovery/CSV_SAMPLE_ASSESSMENT.md`.

| Property | Required value | Status/source |
|---|---|---|
| Columns, order and data types | 76 in supplied order; semantics TBD | Source map required |
| Header row | TBD | None observed; must be confirmed |
| Delimiter | `|` | Confirmed as part of supplied layout |
| Character encoding / BOM | TBD | Sample is ASCII/no BOM; must be confirmed |
| Quoting and escaping | TBD | None exercised in sample |
| Line ending | TBD | CRLF between rows; final CRLF absent; intent unknown |
| Trailing-space preservation | TBD | Critical for fixed-width MILSTRIP |
| Date/time formats and timezone | TBD | Awaiting official layout |
| Trailer/control rows | TBD | Awaiting official layout |
| Filename pattern and extension | Pattern TBD; extension `.txt` | Extension confirmed by Shawn |
| Batch grouping and maximum size | TBD | Awaiting operational rule |
| A5E/address representation | TBD | Awaiting layout/business rule |

The accepted contract must be accompanied by at least one Rainbow-approved
golden file. Tests will compare output bytes, not only parsed CSV values, so
encoding, line endings and trailing spaces cannot drift unnoticed.

## 2. Export eligibility

- `REJECTED`: never exportable.
- `VALID`: expected to be exportable after the official layout rules pass.
- `REQUIRES_REVIEW`: TBD; default-safe behavior is to exclude it until an
  operator explicitly approves it under an auditable rule.
- A batch containing ineligible records: TBD (reject whole batch or export
  eligible rows only).

## 3. Local file behavior

| Property | Required value |
|---|---|
| Output directory | TBD |
| Collision policy | Default proposal: fail; never overwrite silently |
| Temporary local filename | TBD |
| Finalization method | Default proposal: write temporary file, fsync, rename |
| Local retention | TBD |
| Manifest/checksum requirement | TBD |

The serializer will be a pure deterministic component. It will accept eligible
domain records plus explicit export metadata and return exact CSV bytes; it
will not know FTP credentials or perform network operations.

## 4. Rainbow transfer contract — Phase 2C

| Property | DEV/TEST | PROD |
|---|---|---|
| Protocol (SFTP/FTPS/FTP) | TBD | TBD |
| Host and port | TBD | TBD |
| Remote inbound directory | TBD | TBD |
| Remote processed/error directories | TBD | TBD |
| Authentication mechanism | TBD | TBD |
| Secret provider/location | TBD | TBD |
| Source IP allowlist requirement | TBD | TBD |
| Host key / certificate validation | TBD | TBD |
| Timeout and retry policy | TBD | TBD |
| Atomic upload/rename convention | TBD | TBD |
| Duplicate filename behavior | TBD | TBD |
| Delivery acknowledgement | TBD | TBD |

Credentials and secret values must never be placed in this document, source
code, command-line arguments, logs or the `.bat` file.

## 5. Delivery state contract

The implementation must distinguish at least these facts, even if final state
names change during design:

1. input parsed;
2. records approved for export;
3. CSV created and locally validated;
4. transfer attempted;
5. remote delivery confirmed under the agreed acknowledgement;
6. delivery failed or outcome unknown.

An unknown outcome must not trigger an automatic blind resend. Retry and
resubmission use the approved idempotency/duplicate policy.

## 6. Phase 2 acceptance evidence

- authoritative layout and Rainbow-approved golden sample received;
- byte-exact golden and failure-path serializer tests pass;
- `.bat` reports the final local path and never silently overwrites;
- secrets are externalized and logs contain no credentials or payload data
  beyond the approved retention policy;
- safe DEV/TEST transfer proves authentication, path, atomicity and
  acknowledgement behavior;
- timeout, interrupted upload, duplicate name and unknown-outcome tests pass;
- operator SOP verified on the target Windows environment;
- independent Full audit passes;
- HOC explicitly approves production enablement.
