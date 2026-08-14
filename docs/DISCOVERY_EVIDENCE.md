# Discovery Evidence Register

This register states what each source establishes without copying personal
contact details or raw operational correspondence into design documentation.

## Sources reviewed

| Source | Role | Confirmed facts | Limitations |
|---|---|---|---|
| `local-discovery/Initial Idea/MILSTRIP helper NewMultiple_Protoype 1.sql` (local only) | Current production prototype | SQL positions, DODAAC selection, ItemMaster/DODAAC references, duplicate filtering, unconditional staging status, observed Travis variants | Prototype/workaround, not the normative DLM definition |
| Two 2026-08-12 discovery call DOCX files | Current workflow | Manual repair, priority/condition criticality, A5E address, existing downstream boundary | Transcription and verbal evidence; no official field table |
| `local-discovery/0208.12-v2a8.12 (4).docx` (local only) | DLM AP8.12 | A5_/AF6 layout, Stock or Part Number 8-22, `M` quantity rule, family-specific tail/unit price | Does not decide what the Travis SQL currently supports |
| `local-discovery/0208.25-v2a8.25 (1).docx` (local only) | DLM AP8.25 | A2_ layout and its distinct positions 67-80 | Contains a duplicated Distribution row in the source; treated as an editorial duplicate |
| `local-discovery/mail sample with errors.pdf` (local only) | Real intake anomaly, 2026-08-14 | Period/ellipsis spacing contamination, one unique repairable record, one invalid 14-digit numeric identifier requiring DLA correction | Contains personal contact data; only sanitized derived facts enter fixtures/docs |

## Discovery corrections made 2026-08-14

1. Positions 8-22 are one 15-position Stock or Part Number field.
2. Positions 21-22 and 72-73 cannot be discarded as unknown gaps.
3. Quantity is not universally numeric: the DLM defines an ammunition `M`
   suffix form.
4. A2_ and A5_/AF6 do not share one tail schema.
5. Position 70 is Ownership, not Operation.
6. A5_/AF6 positions 74-80 are Unit Price; A2 positions 74-80 are RIC From
   plus Inventory Control Data.
7. Real malformed input now exists, so the earlier statement that no such
   evidence had been collected is superseded.

## Privacy handling

The PDF is retained locally as owner-supplied evidence but is excluded from
Git because it contains names, business email addresses, and telephone
numbers. Tests use structurally equivalent synthetic identifiers while
preserving the punctuation/length anomaly. No corrected value is invented for
the invalid identifier.
