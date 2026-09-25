# Editorial review — web edition 1.5.0

**Date:** September 25, 2026. **Result: PASS — no unresolved editorial finding.**

A reviewer separate from the guide author checked the six procedures against
the four synthetic app screenshots and their control definitions, and inspected
the host-configuration capture. A second read-only chart pass checked all seven
SVGs against their generator and the current deployment evidence. This is an
editorial review, not the production Audit gate or app publication acceptance.

| Measure | Initial edition 1.5.0 | Reviewed edition 1.5.0 | Limit |
|---|---:|---:|---:|
| Complete reading edition | 1,057 words | **994 words** | At most 1,000 |
| Visible operator and overview | 348 words | **328 words** | At most 500 |
| Complete main content with disclosures closed | 474 words | **445 words** | Recorded separately |
| Operator steps | 6 | 6 | 6 |
| Screenshots | 5 | 4 app screens plus 1 host-configuration screen | All reviewed |
| Diagrams | 7 | 7 | All reviewed |

Counts use rendered `main` text and `\b[\w]+(?:[-’'][\w]+)*\b`, including
headings, table cells, captions and disclosure summaries. SVG labels and page
controls are excluded. Closed disclosures contribute their summaries to visible
counts. Chart labels are outside the reading budget; the initial seven charts
contain 1,139 visible words including their version footers.

## Corrections verified

- Removed 63 words, retaining source-ID reconciliation, owner confirmation
  before a new submission, same-command review retry and conflict recovery.
- Opening status identifies the updated intake/administration drafts as
  **unpublished** and specifies that Prod's **database** remains disabled.
- Current architecture chart 02 now says **Host configuration screen** and
  **Database disabled; app opens**, matching the active host authority and
  verified published player.
- Operator chart 03 now says **Owner confirms not saved**, matching the current
  published recovery procedure.
- Transition chart 07 now labels the new drafts **Drafts saved; unpublished**.

## Factual and disclosure checks

The current procedure matches the published controls and captured receipt,
Request ID, saved review/version and `REVIEW_DECIDED` evidence. The current
shared-connection audit identity is accurately distinguished from the planned
individual-user enforcement. Review approval is not presented as downstream
delivery.

New intake completion, the two-hour normalized-content restriction, the audited
Admin/Owner override, and in-app administration remain in the unpublished-draft
disclosure. The hosting plan correctly moves API/gateway off the laptop to TAB
managed hosts, retains Microsoft-hosted Power Apps/Automate, starts with existing
Azure SQL Stage/Prod, and moves to PostgreSQL after migration acceptance. A
connection-string change is not represented as moving history automatically.

The five captures show synthetic examples and a hidden connection-string field;
no secret or raw client order was found in the reviewed public prose/charts.
The rendered reading text and all seven chart text sets pass the existing public
identifier guard. Browser/PDF and package validation were reported by the author;
those checks are separate from this factual/editorial pass. The generated PDFs
contain 13 full-guide pages and four quick-SOP pages, consistent with the reported
build. Documentation publication is editorially ready. This does not accept or
publish the updated native app drafts.

---

# Historical editorial review — web edition 1.2.0

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
