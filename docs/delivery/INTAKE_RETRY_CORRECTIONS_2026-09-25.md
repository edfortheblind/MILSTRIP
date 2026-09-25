# Intake tracking and uncertain-command corrections

**September 25, 2026 — local source implemented; native acceptance pending.**

This correction implements the independent review findings in the earlier
[intake increment](INTAKE_NETWORK_ROADMAP_2026-09-25.md). It performs no database
cutover, private-state change, publication or tenant permission change.

Every new intake now creates its workflow fingerprint in the same transaction,
including requests through the still-published legacy transport. That transport
retains its shared recorded actor; no individual ownership is inferred. The
per-person review gate and two-hour duplicate restriction remain enforced on the
verified broker path. A recent legacy intake therefore remains visible to the
broker's duplicate check after cutover.

Security activation now checks each enabled database's application schema,
environment identity and tracking completeness before changing control state.
Disabled Prod is skipped. **Test draft** cannot issue PASSED while any intake
lacks tracking. These checks only read the database. Missing tracking requires
the existing explicit application-schema initialization/reconciliation process;
the check never invents ownership or silently creates rows. Deploy/restart the
updated writer and finish existing requests before the activation check.

Configuration and user-administration commands retain the original command ID
and frozen payload during lock contention or profile activation, reported as
503. Use **Check command status** or **Retry same command**. Definite configuration
conflicts, such as an outdated draft revision, remain 409 and release the rejected
command so the administrator can discard the draft and reload. User-sharing 409
responses still retain the command: a sharing conflict can follow an already
committed membership change. Status lookup returning no result does not clear an
uncertain command.

**Resume / new intake** no longer treats “no unfinished reviews” as evidence that
an uncertain submission failed. It passes the retained source ID to
`GetIntakeWorkflow`. Only one committed receipt for the exact source ID and the
verified caller resolves uncertainty. Receipts remain discoverable after every
review is complete and when parsing produced zero records. No match remains
**unconfirmed**, because the original request could still be running; multiple
matches remain **ambiguous** and require administrator inspection. The app keeps
the source text and duplicate-override setting frozen while uncertain. It resets
the override after exact receipt confirmation or an ordinary new-intake reset.
An absent receipt never enables a replacement submission.

The broker contract adds optional `source_id` (maximum 200 characters) to
`GetIntakeWorkflow`. Its result retains `active_request_id`, `can_start` and
`duplicate_window_hours`, and adds `source_resolution` and up to two
`source_receipts`. Each receipt contains `request_id`, `source_id`, `status`,
`received_at`, `records`, `rejected`, `requires_review` and `review_complete`.
The server derives the actor from verified broker context. Arbitrary user IDs
are never accepted as lookup inputs.

Verification: **66 focused tests passed**, with two existing dependency
deprecation warnings. Coverage includes isolated in-memory SQL behavior,
activation/configuration rejection, and generated Canvas formulas. The SQLite
fixture does not establish PostgreSQL/Azure SQL acceptance; native Canvas
compilation and published-player acceptance remain separate. Generated Stage and
Prod broker Canvas sources were refreshed locally. Synthetic cleanup routines
now remove the new workflow child rows before deleting their tagged intakes.

The follow-up conflict-classification correction passed **91 focused tests**
with no skips and the same two dependency warnings. Four regression checks
failed before that correction and passed afterward. Real file-lock contention,
profile-drain contention and timeout return 503; a stale configuration draft
returns a definite 409, and a fresh draft can proceed. The same validation run
covered native-run binding, legacy sharing callbacks, activation preflight and
generated Canvas/flow contracts. It used synthetic configuration and no live
database or tenant access.

**DONE_WITH_CONCERNS:** local correction is ready for independent review and
combined-suite validation. Target-database and native-client acceptance are not
claimed by these tests.
