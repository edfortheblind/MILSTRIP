# MILSTRIP Fixed-Width Record Specification

This specification combines the Travis 3PL production prototype and discovery
calls with two DLM 4000.25 Volume 2 appendices supplied on 2026-08-14:

- AP8.12, Materiel Release Order/Follow-Up/Lateral Redistribution Order
  (A5_/AF6 layout; revised 2019-11-26).
- AP8.25, Redistribution Order (A2_ layout; revised 2019-11-26).

The source-to-claim matrix is in `docs/DISCOVERY_EVIDENCE.md`. The DLM files
correct earlier assumptions: positions 8-22 and 72-73 are real data fields,
not disposable gaps, and positions 67-80 have family-dependent meanings.

## Non-negotiable transport contract

- A canonical record is exactly 80 printable ASCII characters.
- Right-trimmed input is accepted from 71 through 80 characters and padded on
  the right; input longer than 80 is rejected and never truncated.
- Every received position is preserved. Canonicalization may pad missing
  trailing positions but must not delete or reinterpret populated positions.
- A deterministic repair is allowed only when collected evidence defines the
  contamination and exactly one expansion satisfies all structural rules.
- Ambiguous or impossible repairs are rejected for human action.

## Common positions, all supported layouts

| Field | Position | Length | Rule/source |
|---|---:|---:|---|
| `dic` | 1-3 | 3 | AP8.25: A2_; AP8.12: A5_ or AF6. Exact third-character support remains subject to the legacy boundary. |
| `ric` | 4-6 | 3 | Routing Identifier Code to the source. |
| `media_status_cd` | 7 | 1 | Media and Status. |
| `stock_or_part_number` | 8-22 | 15 | Stock or Part Number. A numeric NSN is 13 digits plus two blanks in observed Travis traffic; AP8.12 allows type of pack in position 21 for subsistence. Alphanumeric part numbers are valid DLM input. |
| `ui` | 23-24 | 2 | Unit of Issue. Legacy SQL currently replaces it with `ItemMaster.UM1` downstream. |
| `order_qty` | 25-29 | 5 | Five ASCII digits, or four digits plus `M` for the ammunition/FSC categories enumerated by AP8.12/AP8.25. The `M` coefficient must be at least 100 because the represented quantity must exceed 99,999. |
| `requisition` | 30-43 | 14 | Document number. |
| `suffix` | 44 | 1 | Optional suffix/demand position. |
| `supp_addr` | 45-50 | 6 | Supplementary address. |
| `signal_cd` | 51 | 1 | Selects effective DODAAC in the existing SQL rule. |
| `fund_cd` | 52-53 | 2 | Fund code. |
| `dist_cd` | 54-56 | 3 | Distribution data; family instructions differ. |
| `project_code` | 57-59 | 3 | Project code. |
| `priority_cd` | 60-61 | 2 | ASCII `01` through `15` for the current Travis workflow. |
| `rdd` | 62-64 | 3 | Required Delivery Date/Period. |
| `advice_cd` | 65-66 | 2 | Advice code. |
| `ownership_cd` | 70 | 1 | Ownership code. Earlier code incorrectly named this `op_cd`. |
| `cond_cd` | 71 | 1 | Supply Condition; required by the current Travis workflow. |

The current PostgreSQL parser preserves the same full 15-character stock/part
value after migration 004. The legacy row mapper supports the original SQL's
13-character lookup only when positions 21-22 are blank. Populated extensions
remain valid input where appropriate but block legacy handoff for review.
Empty stock/part values and non-printable/non-ASCII record characters are
rejected. Malformed DICs are rejected; unobserved well-formed A2/A5 variants
require review.

## A2_ tail: AP8.25

| Field | Position | Length |
|---|---:|---:|
| `date_received` | 67-69 | 3 |
| `ownership_cd` | 70 | 1 |
| `cond_cd` | 71 | 1 |
| `system_management` | 72-73 | 2 |
| `ric_from` | 74-76 | 3 |
| `inventory_control` | 77-80 | 4 |

AP8.25 says positions 67-69 are blank on submission and populated by a
processing point. Travis' collected A2 records instead carry `SMS` in
positions 67-69 and often numeric data in 74-80. That is a real legacy
variant/contradiction, not evidence that AP8.25 uses the A5 price layout. The
parser preserves it and reports it as informational; future submission design
must decide which form the legacy contract expects.

## A5_/AF6 tail: AP8.12

| Field | Position | Length |
|---|---:|---:|
| `originating_ric` | 67-69 | 3 |
| `ownership_cd` | 70 | 1 |
| `cond_cd` | 71 | 1 |
| `management` | 72 | 1 |
| `intra_service_agency` | 73 | 1 |
| `unit_price` | 74-80 | 7 |

The numeric values observed in positions 74-80 of A5A/A5E examples are
consistent with the DLM unit-price field. The current prototype's unused
`@milsPrice` variable does not consume them, so preserving a value does not
imply it is used downstream.

## Effective DODAAC

The Phase 1 structural calculation mirrors the prototype:

```text
signal_cd < "J"  -> requisition[0:6]
signal_cd >= "J" -> supp_addr
```

The selected source must not be blank. Existence in `cfg_dodaac_active` is a
future database-backed reference validation.

## A5E and AF6 boundaries

- A5E requires an out-of-band ship-to address before submission. Phase 1
  reports `REQUIRES_REVIEW`; it never invents the address.
- AF6 is recognized by AP8.12, but its end-to-end behavior through the present
  Travis SQL has not been verified. It remains `REQUIRES_REVIEW` until the
  future legacy contract explicitly supports or rejects it.
- The DLM `M` quantity is structurally accepted only for eligible categories
  and values, but remains `REQUIRES_REVIEW`: the current SQL performs an
  integer cast on positions 25-29 and cannot consume `1950M` unchanged.

## Evidence-backed punctuation repair

The 2026-08-14 email PDF contains ASCII periods and the Unicode ellipsis glyph
where fixed-width blanks were compressed. Repair is limited to that exact
collected A2 shape: two periods after Stock/Part Number, one after Document
Number, then two ellipses around the known middle/tail segments. Punctuation
anywhere else is rejected, never generalized into a space. The reconstructed
shape must still pass all structural validators.

One supplied record has a unique repair and remains `REQUIRES_REVIEW`. The
other contains a numeric 14-digit stock identifier; the operator explicitly
identified it as invalid and requested a corrected value from DLA. It is
rejected and is never shortened or guessed.

## Source-of-truth implementation

`milstrip/domain.py::FIELD_SPECS` owns the named positional slices for positions
1-71. Positions 72-80 remain intact in `Fields.source`; the current parser does
not expose separate named fields for that tail. The
canonical builder uses the validated normalized source record directly, so a
round trip must equal `normalized.ljust(80)` byte-for-byte.
