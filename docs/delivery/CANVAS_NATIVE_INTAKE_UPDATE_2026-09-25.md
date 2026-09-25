# Native intake and administration drafts — September 25, 2026

**DONE_WITH_CONCERNS: both native Studio drafts are saved and their executable
exports match generated source. Neither draft is published.**

The September 25 changes are now implemented in the existing Stage and Prod
Power Apps drafts. The deployment lead updated Intake, Configuration and Users,
and App.OnStart, then saved and exported each app from Studio. This includes
resume/new-intake handling, the Admin/Owner duplicate override, automatic
database-provider selection and the in-app Initialize database action.

A separate read-only verification compared each native `Controls/` JSON export
against its complete generated environment source. Comparison ignores whitespace
outside quoted Power Fx strings and preserves string contents. It checks the
executable rules, including values omitted as defaults by Code View. The four
gallery item accessibility labels were checked on their native `galleryTemplate`
children, where Studio persists those properties.

| Verified in each app | Result |
| --- | --- |
| Generated controls | 85 of 85 match; none missing or unexpected |
| Generated control properties | 724 of 724 match |
| Behavior handlers within those properties | 37 match |
| Screen OnVisible handlers | All six match |
| App.OnStart, App.StartScreen and App.Formulas | All three match |
| AppEnvironment named formula | Matches the app's environment |
| Native service and connection binding | Exactly the matching broker; both logical-flow identifiers match |
| Opposite-environment broker or direct API connector | Absent from executable formulas and dependencies |

Each app retains its broker service, the Office 365 Users invoker connection
dependency and two local static data sources. These are native dependency checks;
they do not establish a second user's authenticated runtime behavior.

## Immutable export references

The native exports and detailed comparison reports remain private under `.cred/`.
They contain connection metadata and are not release packages.

| Saved native export | SHA-256 |
| --- | --- |
| `MILSTRIP-Stage-20260925-intake-admin-draft.msapp` | `37400003920f5b98abe31d946dd0e8b488e321ce7db4f6ebb75ecbab02655e37` |
| `MILSTRIP-Prod-20260925-intake-admin-draft.msapp` | `c745b5d7b73c53cec340d2fe893b2ed3b5fb312c423a7065904e32d3010b9f96` |

Safe comparison reports: `native-stage-intake-admin-verification.json` and
`native-prod-intake-admin-verification.json`. They record counts, formula-match
results, binding checks and App Checker categories without formula bodies,
credentials or connection values.

## Remaining native acceptance limits

Both exports record **ParserErrorCount = 1** and **BindingErrorCount = 0** in
`Properties.json`. Their App Checker SARIF contains two literal-predicate warnings
and 66 accessibility findings: 35 tab-index findings, 27 focus-border findings
and four accessible-label findings. These categories match the
[September 24 draft evidence](CANVAS_SOURCE_ASSEMBLY_2026-09-24.md). No parser-error
finding appears in the SARIF, so the disagreement with `ParserErrorCount` remains
unresolved. This is not evidence of a zero-parser-error app.

Executable source equivalence does not establish runtime acceptance. The native
broker flow definitions still need the corresponding update and readback, and
the interactive permission-read path needs complete, accepted verification before
sharing retries or access-control cutover. Then verify second-user identity,
role enforcement, configuration recovery, intake completion and duplicate
behavior in the native app. The known accessibility findings also retain their
[native acceptance requirements](CANVAS_ACCESSIBILITY_2026-09-24.md).

These saved drafts do not change the currently published player. No Canvas
publication, production database connection or security-enforcement activation
was performed by this draft update or its independent verification. Deployment
and runtime gates remain in the
[intake and hosting roadmap](INTAKE_NETWORK_ROADMAP_2026-09-25.md).
