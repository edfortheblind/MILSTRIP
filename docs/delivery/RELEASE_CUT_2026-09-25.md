# Owner-requested release cut — September 25, 2026

**Historical pause at the owner's request, around 17:02 UTC / 12:02 CDT.**

The owner subsequently resumed work. Read [master](../master.md) and the
[native pilot acceptance](NATIVE_PILOT_ACCEPTANCE_2026-09-25.md) for current
status; the facts below describe the cut, not the resumed deployment.
Browser, tenant and agent work stopped. Existing services were left running.
Resume only when the owner requests it. Prior commit/push/publication approval
persists; this checkpoint does not authorize work during the pause.

## Completed

- Private core commit: `43126a09db192cc5795ab7d92faf3edbadf4c750`.
- Private guide commit: `5fc68d043babaec32c7976c24404983fd9d6d086`.
- Public guide commit: `0c54fdc0e2d6779954ed799974ad7eccd4fe5afa`.
- [Guide 1.5.0 is live](https://edfortheblind.github.io/milstrip-guide/).
  Pages built the exact commit; anonymous HTTP200 matched the committed HTML:
  2,156,505 bytes, SHA-256
  `1edc851bb7f33a5433fee3683d14c82ef56a4fc42c4e3a317bae5a9942072136`.
  Offline/render/navigation/print/mobile/PDF/package and editorial checks passed.
  The guide correctly describes the new app behavior as unpublished drafts.
- Full local suite: **747 passed, zero skipped**, two upstream warnings,
  150.62 seconds, including approved local PostgreSQL integration. Separate
  final reader/flow/package review: 191 passed. Pagination is not implemented
  and therefore is not covered by these results.
- Both six-screen Canvas drafts are saved/exported, **not published**.
  Independent executable comparison passed per app: 85 controls, 724 properties,
  37 behavior handlers, 6 screen events, 3 App properties. See
  [native evidence](CANVAS_NATIVE_INTAKE_UPDATE_2026-09-25.md).

## Preserved runtime state

Existing published apps remain in place. Prod opens with its database disabled;
Stage uses local PostgreSQL. Both broker flows remain Started with older
definitions; the new allowlist/native-run binding and permission-reader source
are not deployed. Local API remains running with current code.

Last private control readback: 3 ACTIVE users, 3 PENDING, zero sharing leases,
security enforcement inactive, runtime authority inactive. The historical canceled
sharing execution was already recovered using fresh authenticated evidence.
Do not repeat recovery, clear leases manually, or disable pending users to bypass
activation. No new permission grant, Azure SQL connection, DNS change or
production database cutover occurred in this diagnostic increment.

## Confirmed blocker

The native HTTP with Microsoft Entra ID (preauthorized) fixed Stage GET and
`json(string(body(...)))` parsing succeeded with protected run history.
Safe scalar diagnostics established first-page count 2, nextLink=true,
@odata.nextLink=false,error-key=false. The continuation matched
`api.powerapps.com` and the fixed Stage permissions path, with exactly three
ordered query keys:`api-version`, `%24filter`, `%24skiptoken`.

Earlier host diagnostics collected 3 aggregate assignments per app; they retain
no page count and never proved a single native page complete. The trial's
expected count 3 on page 1 was therefore invalid. No completeness guard was relaxed.

The current source makes one fixed GET per observation and rejects continuation.
It is tested but cannot resolve sharing acceptance. The private package
`.cred/broker-finite-permission-reader/` was built, **never imported**; SHA-256
`a850d0ef79b29731654aa5d03b1acb1f0404d5b71cd6fcd5216540e34f7a631e`.
Do not import it. Rebuild only after the reviewed pagination implementation.

The [three-page addendum](FINITE_PERMISSION_READ_DESIGN_2026-09-25.md) is an
unfinished proposal: explicit protected page actions, sibling conditional
branches, strict fixed-route cursor validation, cumulative row/identity proof,
terminal completion and deadline checks before writes. No cursor/row variables
or automatic pagination. Exact cursor grammar/fixed-value encoding and proposed
time budget still need review. Baseline 265 actions; count the entire new graph
against action/nesting/expression limits before deployment.

## Native diagnostic and private artifacts

Unshared manual flow **MILSTRIP Permission Read Validation** contains only the
fixed Stage GET and scalar diagnostics. Its latest intentional failure exposes
only allowlisted cursor-shape labels, not permission rows. A second HTTP action
or Parse JSON extension was not saved/executed before the pause. The browser
may retain an add-action search panel; inspect current state before editing.

- Existing solution:`6e8f0ea9-63b7-f111-aaac-7ced8d6f317c`.
- Diagnostic flow:`77cd570c-ffb8-f111-aaac-7ced8d6f317c`.
- Connected named connection:`MILSTRIPPermissionReadSSO`,
  `f468112b08ef428e88a3f2a3ea33258a`. The designer also created a second normal
  SSO connection/reference used by the diagnostic; reuse existing resources.
- Connection base:`https://api.powerapps.com`; audience:
  `https://service.powerapps.com/`.
- Private bindings:`.cred/broker-flow-bindings.json`; prior backup:
  `.cred/broker-flow-bindings-before-permissions-20260925.json`.
- Private exports:`.cred/MILSTRIP-Stage-20260925-intake-admin-draft.msapp`
  and matching Prod export; safe diagnostics/screenshots:`.cred/permission-*`.

Rediscover browser handles and tab order. Mouse actions require the intended
browser in front; avoid generic Close selectors. Use normal sign-in, never
export tokens, unmask permission records or open protected content links.
An SDK flow-lookup command was rejected by automatic approval review with
"blocked by policy" and did not run. Native UI successfully supplied the flow
ID instead; do not retry the rejected command.

## Resume sequence

1. Finalize/review pagination design; implement and test complete traversal,
   invalid/repeated/cross-resource cursors, duplicate identities, page/row bounds,
   deadlines and suppression of writes after any failed/incomplete observation.
2. Prove protected native traversal for BOTH apps; independently review source,
   generated limits and bindings before updating the existing broker flows.
3. Complete the three pending memberships using existing commands/lease rules.
   Verify actual caller identity with a second configured TAB user; that
   availability question was unanswered at the pause.
4. Complete security/runtime activation, legacy-identity rejection and native
   configuration/intake/review/duplicate behavior acceptance.
5. Refresh Studio Formula errors: exported Parser count 1 has no message/location
   and is not proven harmless. Binding count 0; two literal-filter warnings and
   66 accessibility items are documented baseline findings. The accessibility
   items flag inert labels/galleries/decorative images, not active controls.
6. Publish both accepted Canvas drafts, update the guide to actual released
   behavior/screens, verify publication, commit and push. Hostname deployment
   and Azure SQL target acceptance remain later work.
