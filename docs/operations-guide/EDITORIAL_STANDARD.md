# MILSTRIP documentation standard

Applies to the public operator guide, SOP, navigation, captions, charts and
release notes. A separate editorial reviewer checks each publication. This is a
documentation review, not the production Audit gate.

## Reader and scope

The operator needs to complete a task and recognize its outcome. Put the normal
procedure first, recovery second, and engineering plans in closed disclosures.
Keep production design evidence in the engineering notes rather than reciting it
in the operator procedure.

## Writing rules

1. Write an action, its observable result, or the exception that changes the next
   action. Remove sentences that do none of these.
2. Use exact visible control labels. Confirm each label and result against the
   current control source and captured screen before publishing.
3. Give each fact one home. State the current scope once; avoid repeating it in
   captions, steps, footer and side cards.
4. Mark current and proposed behavior explicitly. Never use a planned
   acknowledgement as evidence of a live integration.
5. Name the evidence behind success: Request ID, persisted review version, audit
   event, handoff reference or downstream receipt. Procedure completion is not
   interchangeable with downstream acceptance.
6. Use plain titles and complete instructions. Avoid slogans, rhetorical
   questions, staged contrasts, motivational closings, sales language and
   repeated explanations of the same boundary.
7. Keep identifiers and recovery branches that prevent duplicates or lost work.
   Brevity must not erase the difference between intake reconciliation and
   retrying the same review command.
8. Captions describe the visible state rather than repeat the procedure.
   Use real, sanitized screens and provide readable enlargement.

## Size limits

- Six operator steps, each with one action heading and one short paragraph.
- At most 500 words of visible operator and overview prose, excluding closed
  troubleshooting and planning disclosures.
- At most 1,000 words across the reading edition, excluding SVG labels and page
  controls. Count headings, table cells and disclosure summaries.
- Keep detailed contracts and evidence in engineering notes. If a necessary
  operator exception exceeds the budget, have the editorial reviewer document
  why rather than silently deleting it.

## Publication review

A reviewer other than the author performs the following pass without asking the
owner to line-edit:

- Follow the six steps against the screenshots and control definitions.
- Identify the exact evidence of submission and review success.
- Check unknown submission, unknown review and version conflict recovery.
- Flag any claimed downstream action without implementation evidence.
- Remove duplicated facts and sentences with no operational purpose.
- Check title, navigation and captions by the same standard as the main text.
- Record word counts, screenshot/step counts, unresolved findings and result.

The owner reviews business decisions and the finished page. Editorial cleanup is
the implementation team's responsibility.
