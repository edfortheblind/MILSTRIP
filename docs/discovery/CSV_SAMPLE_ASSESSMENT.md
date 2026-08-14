# Shawn CSV Sample — Evidence Assessment

**Status:** Layout and `.txt` extension confirmed by Shawn; field contract incomplete

**Source handling:** Raw files remain under Git-ignored `local-discovery/` and
must not be committed.

## What was supplied

`MILSexamples.csv` and `MILSexamples.txt` are byte-for-byte identical. They are
one artifact presented with two extensions, not two independent examples.

Observed byte-level properties:

| Property | Observation |
|---|---|
| Size | 2,182 bytes |
| Encoding | 7-bit ASCII; no BOM |
| Delimiter | Literal pipe (`|`), despite the `.csv` extension |
| Rows | 6 data rows |
| Fields | Exactly 76 fields in every row |
| Header/trailer | None observed |
| Quoting | None observed |
| Line separation | Five CRLF separators |
| Final line ending | No final CRLF |
| Physical row length | Variable, approximately 315–481 bytes |
| DIC coverage | Three A2A, one A5A and two A5E rows |

The rows are not 80-character fixed-width MILSTRIP records. They include a
requisition-like value and NSN-like value, but also contain address, contact,
timestamp, price/order and other enriched data. Some populated values are not
derivable from the canonical MILSTRIP alone. The sample therefore resembles a
database or downstream interface extract.

## What the sample does not prove

Shawn subsequently confirmed that the artifact represents the file layout and
that `.txt` is the correct extension. It still does not establish:

- Rainbow accepted or consumed these exact bytes;
- all 76 fields are required or in an authoritative order;
- the last row must omit CRLF;
- ASCII, empty fields, leading spaces or the observed decimal/date formats are
  contractual rather than incidental;
- literal pipes, quotes, CR/LF or non-ASCII values are impossible;
- the application is responsible for the enriched address/contact data;
- filename, batching, ordering, duplicates or acknowledgement behavior can be
  inferred.

Because the file has no header or companion dictionary, assigning semantic
names to column numbers would be speculation. The sample is useful for
characterization tests only after sensitive values are replaced with approved
synthetic equivalents. It is not yet a production golden file.

## Architectural impact

If this is the actual Rainbow input, Phase 2 may require reference/database or
operator-provided enrichment before it can generate the file. That conflicts
with the current plan to defer database work to Phase 3 and must be resolved
explicitly. If this is an output from Rainbow or another downstream stage, it
does not define the application's export contract at all.

The raw examples also include operational address/contact content. Saving the
future output to Desktop requires an approved retention/access policy. A
machine-interface artifact must not be opened and resaved in Excel unless
Rainbow defines how formula-like values, leading spaces and text identifiers
are preserved.

## Verdict

**STRUCTURE CONFIRMED / INSUFFICIENT FOR SERIALIZATION.** Obtain the 76-column
source map, byte edge-case rules and accepted/ACK evidence before building the
production serializer.
