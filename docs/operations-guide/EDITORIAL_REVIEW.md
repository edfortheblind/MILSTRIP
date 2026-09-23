# Editorial review — web edition 1.2.0

**Date:** September 23, 2026. The owner requested professional operator
instructions without slogans, repeated caveats or lengthy demonstration prose.

The `principal_sop_editor` agent rewrote the guide and generator text. A separate
`acknowledgement_review` agent checked the procedure, acknowledgement semantics
and all four real screenshots. These are AI editorial roles, not a claim of
human credentials or the project's independent production Audit.

## Changes

| Finding | Revision |
|---|---|
| Repeated framing before the procedure | Removed the slogan, three status cards, duplicate jump links and repeated footer caveats |
| Competing operator and engineering audiences | Retained six actions beside four screens; moved recovery and technical planning into disclosures |
| Confirmation insufficiently explained | Distinguished intake storage, production handoff and downstream receipt; added the current receipt to Results |
| Procedure/chart numbering differed | Aligned the operator diagram with the six illustrated steps |
| Counts could imply outstanding review work | Labeled receipt counts **Validation at intake** and **Flagged for review** |
| Production lookup scope overstated | Replaced stock-check wording with item/address lookup wording |
| Receipt diagram could imply all handoff outcomes proceed | Labeled the downstream arrow **accepted handoff**; receipt records accepted/rejected separately from shipment |
| Repeated editing required owner intervention | Added the reusable [editorial standard](EDITORIAL_STANDARD.md), including size limits and a separate publication review |

## Measured reduction

Both editions were rendered from Markdown with the same parser and counted with
`\b[\w]+(?:[-’'][\w]+)*\b`. Counts include headings, table cells, image captions,
disclosure summaries and disclosed prose. SVG labels and page chrome are excluded.
The baseline is the guide at source commit
`b45c6f2c0f002ea0e33ee0c8e182b03461c39b69`.

| Measure | Before | Edition 1.2.0 |
|---|---:|---:|
| Complete reading edition | 1,601 words | 876 words |
| Reduction | — | 45.3% |
| Visible operator and overview | — | 345 words |
| Complete page with disclosures closed | — | 464 words |

The independent review passed the procedure and four captures. Its terminology
and diagram findings above were applied. The rebuilt page passed screenshot,
step, chart, interaction, text-bound and responsive-layout checks. The complete
PDF has **12 pages**; the illustrated SOP has **four pages**.

Current receipt evidence and remaining production contracts are documented in the
[acknowledgement design](../delivery/ACKNOWLEDGEMENT_DESIGN_2026-09-23.md).
Production integration acceptance remains outside this editorial review.
