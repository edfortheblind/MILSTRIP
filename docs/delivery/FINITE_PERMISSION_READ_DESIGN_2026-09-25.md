# Finite native app-permission read

**Status: paused by owner September 25. Single-page source is tested but fails native completeness acceptance. Three-page extension is an unfinished proposal. Do not import the candidate or retry sharing.**

The Makers connector's app-role GET returned continuation markers in earlier
sharing runs. Enabling automatic pagination then stalled the first read for more
than eight minutes. The canceled run has been reconciled separately; its pending
membership is not permission evidence. See the
[historical trial](MAKERS_PERMISSION_PAGINATION_2026-09-24.md) and
[recovery implementation](SHARING_RECOVERY_IMPLEMENTATION_2026-09-25.md).

## Initial single-page decision

Replace only the eight app-permission read actions in each broker flow with a
single explicit HTTP GET through **HTTP with Microsoft Entra ID (preauthorized)**.
Keep the existing Makers permission writes, Flow Management operations, durable
sharing lease, Management permits, caller authorization and reconciliation.
No pagination loop, caller-supplied URL, cursor, new host, application registration
or copied credential belongs in this change. Operators and application managers
continue to use the existing Power Apps screens.

The published [Makers operation](https://learn.microsoft.com/en-us/connectors/powerappsforappmakers/)
accepts app, API version and page size, but no cursor input. The corresponding
[Admins operation](https://learn.microsoft.com/en-us/connectors/powerappsforadmins/)
also lacks a cursor input, so changing to that connector does not solve traversal.

## Fixed connection and requests

Use one embedded deployment connection in the existing TAB environment, with
the normal TAB deployment owner's sign-in. Do not add this connection as an
invoker connection or Canvas data source.

| Setting | Fixed value |
|---|---|
| Confirmed connector | `shared_webcontents` |
| Connection base resource URL | `https://api.powerapps.com` |
| Microsoft Entra resource URI | `https://service.powerapps.com/` |
| Confirmed operation | `InvokeHttp` |
| Method | `GET` |
| Request body | None |
| API version | `2017-06-01` |
| Environment | `Default-9f5c0ace-0780-4b48-8c24-b08bb5149210` |
| Stage app | `7f1b64d0-d51a-4ec8-84ad-2b18fe8c2f82` |
| Prod app | `0aa02d8b-c7fa-42cc-87e8-6d287bd4c897` |

An authenticated, fixed-route native metadata read at 16:12:28 UTC confirmed the
connector ID `/providers/Microsoft.PowerApps/apis/shared_webcontents`, operation
`InvokeHttp`, and no `x-ms-pageable` declaration. Its adapter route is
`POST /{connectionId}/codeless/InvokeHttp`; the requested service method remains
`GET`. The body parameter is `request`, referencing `HttpRequest`, which requires
`method` and `url` and optionally accepts `headers` and `body`. Generate the
parameter leaves `request/method` and `request/url`; omit `request/body`.
The connector's default response schema is unconstrained, so native metadata
alone does not establish the returned content's runtime wrapper.

Generate a literal, environment-specific URL for each read:

```text
https://api.powerapps.com/providers/Microsoft.PowerApps/apps/{fixed_app_id}/permissions?api-version=2017-06-01&%24filter=environment%20eq%20%27Default-9f5c0ace-0780-4b48-8c24-b08bb5149210%27
```

Braces above describe generation-time substitution only. Runtime app, host,
environment and query inputs are never accepted from the caller. Do not add
`$top` during the initial trial: use the exact route already exercised by the
finite host diagnostic. That diagnostic succeeded for Stage on September 25 at
16:06:05 UTC and Prod at 16:09:23 UTC, each with three assignments and the
authenticated deployment Owner.
It establishes API-route reachability, not the new connector's acceptance or
the number of pages it read.

Microsoft documents [this connector](https://learn.microsoft.com/en-us/connectors/webcontents/)
as premium, delegated and preauthorized for selected Microsoft services; full
URLs must match the connection's base URL. Its documentation does not guarantee
authorization to every resource. Microsoft's
[Power Shield setup](https://learn.microsoft.com/en-us/microsoft-copilot-studio/guidance/kit-power-shield)
uses the same `service.powerapps.com` audience with this connector for a different
Power Platform API host. The exact app-permission route still requires a native
connector trial.

## Required result contract

Each observation makes exactly one request. Disable retries and automatic
pagination. Protect HTTP inputs/outputs and all parsing/filtering actions in run
history. Keep only fixed reason codes in public diagnostic output.

Confirm the actual native response wrapper before wiring expressions. The
connector documentation describes response content as a body string; if native
metadata confirms direct response content, a protected JSON parser can normalize
it with `json(string(body('HTTP_read')))`. Require a JSON object containing a
`value` array. A missing array, malformed JSON, error envelope or failed parser
is not an empty permission list.

An observation is complete only when all these checks pass:

- The HTTP and parsing actions succeeded and the native response is successful.
- `value` is an array with fewer than 1,000 rows.
- Both `nextLink` and `@odata.nextLink` are absent, null or empty strings.
- Assignment IDs/names bind to the fixed app; principal, tenant, type and role
  have the expected shape. Reject duplicate or ambiguous target assignments.
- The exact issued sharing plan still matches the target and fixed resource.

Keep the existing Owner exception limited to the pinned deployment owner;
ordinary approved users require `CanView`. A malformed or incomplete before-read
suppresses its permission mutation. A malformed or incomplete after-read leaves
the membership pending. Never infer absence from a failed read, use an earlier
diagnostic as live authorization, follow a continuation automatically, or report
membership active from the permission-write response alone.

This design deliberately supports complete small-result pages. A future larger
result that paginates remains pending and requires a separately reviewed finite
traversal change. The 1,000-row rule is an acceptance limit, not a transport-size
guarantee.

The native trial below confirmed that the current small result also paginates.
The following addendum therefore supersedes the one-page limit for the next
candidate; it preserves the response, identity and before/after safety checks.

## Timing and tenant prerequisites

One nonaggregating request removes the unbounded pagination behavior. It does
not establish a 30-second hard deadline: the HTTP connector exposes no documented
per-request timeout or redirect-disable parameter. Microsoft documents a
[120-second synchronous request limit](https://learn.microsoft.com/en-us/power-automate/limits-and-config).
Do not claim a Power Apps timeout cancels the flow or releases a durable lease.
The existing cancellation/recovery rules still apply.

The normal TAB connection owner needs read authority on both fixed apps; existing
write connections retain their existing authority. Verify premium use rights and
that the connector may coexist with the existing connectors under TAB's data
policy. If a policy restricts endpoints, use these literal URLs so the supported
[static endpoint checks](https://learn.microsoft.com/en-us/power-platform/admin/connector-endpoint-filtering)
can evaluate them. No policy relaxation is assumed.

Try the preauthorized connector through normal sign-in. If it produces a consent
or scope failure, preserve the fixed error code and stop the trial. Switching to
the [non-preauthorized connector](https://learn.microsoft.com/en-us/connectors/webcontentsv2/)
requires explicitly identifying the service's delegated scopes and the documented
administrator consent process; it is a different design decision. Do not infer a
scope from Dataverse permissions or request tenant-wide consent speculatively.

## Trial and release gates

1. Use the confirmed connector ID and operation schema; map a normal TAB
   connection in the existing environment/solution and confirm that the native
   designer serializes the two parameter leaves above.
2. Execute only the two fixed read requests, with protected content. Record
   success, row count, completeness and fixed error codes. Do not retry sharing
   or modify permissions as part of this trial.
3. Implement the generator and parser guards. Test successful complete pages,
   missing/non-array values, both continuation keys, row limits, malformed or
   cross-app assignments, ambiguity and connector/parser failure. Independently
   review the resulting flow and confirm native protected-run settings.
4. Deploy the reviewed broker definitions, including the current operation
   allowlist and native-run lease binding. Then perform the authorized in-app
   sharing acceptance and second-user identity checks.
5. Complete the existing enforcement/cutover checks before publishing both
   Canvas drafts. Prod's database remains disabled until its separate target
   acceptance. Hostname readiness is a later infrastructure step.

Publication approval does not turn the read-only diagnostic into a completed
sharing trial. Source checks, connector acceptance, user sharing and final
publication are separate evidence gates.

## Addendum: three explicitly generated pages

### Evidence and scope

The native Stage HTTP request and `json(string(body(...)))` parsing succeeded
with protected history. Separate scalar diagnostics established:

| Native first-page fact | Result |
|---|---|
| `value` count | 2 |
| Nonempty `nextLink` | true |
| Nonempty `@odata.nextLink` | false |
| Top-level `error` key | false |

The earlier finite host diagnostic collected three assignments. That aggregate
never established a single-page response. The native first page is incomplete;
two rows cannot prove that the requested user is absent. No permission write is
authorized by this trial. A later protected native diagnostic confirmed the
exact `api.powerapps.com` host, selected Stage permissions path, and three query
keys in order: `api-version`, `%24filter`, `%24skiptoken`. Cursor value grammar
and exact fixed-value serialization remain unverified. No cursor value or
permission record was exposed. Finalize and independently review the validator
before implementation.

The next candidate will generate three page slots for each app-permission
observation: one fixed initial GET and at most two continuation GETs. It keeps
the existing HTTP Entra connection and the existing before-read, mutation and
fresh after-read sequence. Do not add an Until/For each loop, automatic
pagination, retry policy, dynamic variable, caller URL parameter, authentication
service or token export. Each continuation slot is conditional; completing page
one or two skips the remaining requests.

### Protected continuation validator

First obtain safe native shape evidence: whether the URI is absolute; exact
host/path agreement; query-key names and order; duplicate-key presence; cursor
encoded length/character classes; and whether the fixed API version and
environment filter remain present. Inspect none of the cursor values, assignment
rows or signed content links in visible history. Keep the diagnostic inputs
protected and expose only fixed scalar classifications. Prove the same permitted
shape for both apps before release.

Use a protected Parse JSON action on a small object containing the selected
continuation string. Its generated schema must require that string, cap its
length at 16,384 characters, and match the **whole serialized URI**. The design
is a finite allowlist of one canonical serialization form, or two if the native
evidence requires both; it is not a permissive URL parser. Schematically:

```text
FORM_1 := LITERAL_FIXED_ORIGIN_AND_APP_PATH + '?' + OBSERVED_FIXED_QUERY_ORDER_1
FORM_2 := LITERAL_FIXED_ORIGIN_AND_APP_PATH + '?' + OBSERVED_FIXED_QUERY_ORDER_2
```

These are design placeholders, not executable patterns. Generate the actual
anchored patterns only after observing the cursor shape. Escape every literal
segment, including query separators. Each admitted form must contain:

- Exactly `https://api.powerapps.com` and the selected fixed app's
  `/providers/Microsoft.PowerApps/apps/{app}/permissions` path. No alternate
  host, port, user information, fragment, path encoding or dot-segment form.
- Exactly API version `2017-06-01` and the exact existing environment filter,
  encoded in the observed canonical form. Neither may be omitted or repeated.
- Only the observed cursor key or keys, each exactly once, with bounded,
  observed value syntax. No optional arbitrary query suffix or wildcard `.*`.
  Cursor character classes must exclude raw separators that could add a query
  key. Admit percent escapes only as complete hexadecimal triplets where the
  native serialization uses them; admit numeric cursor components only with
  their separately bounded numeric syntax.

Reject raw controls, whitespace and backslashes separately, including a final
newline: a regular-expression `$` anchor alone may match before that newline.
The fixed literal prefix excludes encoded-path normalization and user-info
tricks before query parsing. Fixed, uniquely placed query delimiters exclude
duplicate API-version, filter or cursor keys. Unexpected ordering, extra keys,
missing scope or a changed cursor format must fail closed, even if the service
might otherwise accept them.

After schema success, protected Compose actions may extract cursor components
using only the validated literal delimiters and reconstruct one canonical URL
from the fixed origin/path/version/filter plus those components. When two
serialization forms are allowed, normalize them to the same representation so
equivalent continuations cannot defeat repeated-cursor detection. The encoding
rules must preserve the opaque cursor's value; do not guess how plus signs or
percent decoding behave. If that cannot be proved from the observed format,
retain one strict form or stop for a revised design.

Select `nextLink` or `@odata.nextLink` only after checking their types. A present
value must be a string or null. Two nonempty values must be exactly identical;
otherwise reject the page. Compare each canonical next request against the
initial route and all preceding requested routes. Repeated routes/cursors are
incomplete, never evidence of exhaustion. The validated cursor has authority
only within this app observation, not another app, plan or run.

Both raw and canonical continuation URLs remain protected. HTTP Entra's base
URL restriction supplements these checks. Do not rely on DLP to validate a
dynamic continuation expression: Microsoft documents that
[endpoint filtering does not evaluate dynamic endpoints](https://learn.microsoft.com/en-us/power-platform/admin/connector-endpoint-filtering).
If TAB's actual policy prohibits the candidate, report that result without
relaxing the policy.

### Page chain, aggregate proof and terminal selection

Create page-two and page-three guards as **siblings** of page one, not recursively
nested guards. A guard consumes only a protected validation result reduced to a
boolean. Page two requires valid page one, a valid new continuation and an
unexpired deadline. Page three additionally requires valid page two and its new
continuation. Each later HTTP action uses only the preceding validator's
canonical URL. No connection, request or validation error starts a later page.

Every fetched page must pass the existing required-array/error-envelope schema,
fixed-app ID/name binding, safe token/path rules, GUID tenant/principal checks,
accepted roles/types and per-page duplicate checks. Reject an oversized page
before starting another request. A valid empty page with a new continuation is
not terminal and still consumes a page slot.

Maintain the following cumulative proof in protected Compose/Select outputs:

- All fetched pages belong to the same fixed app, tenant, sharing plan and
  observation phase, and every required HTTP/parser/projection action succeeded.
- The **sum** of page row counts is less than 1,000. This remains an acceptance
  bound, not a guaranteed HTTP response-size limit.
- The summed ID-projection count equals the length of the union of all normalized
  assignment-ID projections; apply the same check to principal-ID projections.
  This rejects an identical repeated row and a repeated ID with different role
  or payload fields. Never use `union()` first and then count the deduplicated
  rows as if the original responses were unique.
- There is at most one target-principal assignment across all pages. Preserve
  the existing User/CanView rule and the pinned deployment-Owner exception.
  Elevated or unexpected target grants do not become verified absence.

A protected terminal-selection Compose identifies page one, two or three only
when that page and its complete required prefix are valid and its selected
continuation is empty. A page-two/three action skipped because an earlier page
already completed is optional; a required page skipped, failed or timed out is
incomplete. Do not manufacture an empty page for any failure. If page three
still has a cursor, return a fixed page-limit diagnostic and leave pending.

Build the effective permission array only from the validated terminal prefix,
after cumulative uniqueness passes. The before-read mutation gate requires
this complete proof and the still-matching issued sharing plan. Run a wholly
new page chain after any mutation; before-read rows/cursors are never reused as
after-read evidence. A failed or incomplete after-read leaves membership pending
and retains existing unknown-outcome/lease handling. Read completion never
proves that a permission write succeeded by itself.

### Privacy, deadlines and generated limits

Protect every HTTP, Parse JSON, Query, Select and Compose that handles URLs,
rows or identity projections, including downstream aggregates. Use the existing
inputs-only protection for Compose/Parse JSON, which also hides their outputs.
Do not rely on automatic propagation to later actions. Microsoft lists variable
actions as unsupported for secure inputs/outputs; opaque cursors and assignment
IDs are not approved substitutes for protected state. This candidate uses no
dynamic variables, even for counters. Its page count is fixed by the generated
graph. [Run-history protection](https://learn.microsoft.com/en-us/azure/logic-apps/logic-apps-securing-a-logic-app)

Use a protected start timestamp and a proposed **90-second observation budget**.
Recheck elapsed time before each continuation request, when selecting a complete
result, and immediately before a permission write. Exhaustion means pending;
it does not authorize cleanup or release a possibly active/uncertain lease.
This budget prevents starting later work after expiry. It cannot interrupt an
in-flight managed-connector call or promise a response inside Power Apps'
synchronous limit. The three-page maximum is a hard request-count bound for one
observation; a run must never continue automatically into a fourth page. The
existing cancellation and evidence-based recovery rules remain necessary.
Microsoft explicitly documents that an
[Until timeout does not interrupt its current iteration](https://learn.microsoft.com/en-us/azure/logic-apps/logic-apps-control-flow-loops).

The source baseline has 265 actions per flow, including eight app-permission
observation sites across add/remove branches. Expanding each site to three slots
permits at most 24 statically defined app GET actions; only the selected branch
executes. Before any import, count the **entire** generated graph and enforce
500 actions, at most eight enclosing action containers, action names of at most
80 characters and expressions of at most 8,192 characters. The baseline already
has deeply nested write branches; sibling page guards must not deepen them.
Do not assert that the extension fits merely from the number of GETs. If the
full expansion exceeds a limit, stop and revise the design rather than raise a
limit or drop a guard. [Flow definition limits](https://learn.microsoft.com/en-us/power-automate/limits-and-config)

### Extension acceptance gates

1. Record the safe native continuation shape, then review the exact one/two-form
   URI patterns and opaque-value normalization. A first page's continuation
   flag alone is not sufficient to write this validator.
2. Test the generated chain offline for one/two/three-page completion, conflicting
   or malformed cursors, cross-host/app/environment/version routes, duplicate
   keys, encoded path tricks, repeated routes, duplicate identities across pages,
   999/1,000 aggregate rows, empty intermediate pages, final-page continuation,
   all parser/transport failures and deadline exhaustion. Confirm that no failed
   prefix can enable a write or verify absence.
3. Run a protected read-only native traversal for each app, including terminal
   selection and row/identity proof. Test representative valid and invalid URI
   schemas natively so offline JSON-schema support is not assumed to match the
   platform. Expose only status, counts, page count and fixed reason codes.
4. Independently review generated code, limits, connection binding and masked
   history before any broker import or sharing retry. Then retain the original
   sharing, second-user, enforcement and publication gates above.

This addendum authorizes no tenant operation. Implementation awaits native cursor
shape evidence and review of the resulting exact validator.
