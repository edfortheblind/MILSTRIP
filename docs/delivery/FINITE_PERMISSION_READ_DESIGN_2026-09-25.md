# Finite native app-permission read

**Status: resumed September 25. Native evidence requires explicit pagination and rejects Parse JSON regex schemas. The revised design below uses the existing broker for read-only validation. Implementation and native acceptance remain open; do not import the earlier candidate or retry sharing.**

The Makers connector's app-role GET returned continuation markers in earlier
sharing runs. Enabling automatic pagination then stalled the first read for more
than eight minutes. The canceled run has been reconciled separately; its pending
membership is not permission evidence. See the
[historical trial](MAKERS_PERMISSION_PAGINATION_2026-09-24.md) and
[recovery implementation](SHARING_RECOVERY_IMPLEMENTATION_2026-09-25.md).

## Initial single-page decision (historical)

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

## Initial result contract (superseded by the addendum)

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

## Addendum: three pages with internal broker validation

### Native evidence and decision

Protected Stage trials established two first-page rows, a nonempty `nextLink`,
no nonempty `@odata.nextLink` and no error member. The host reader collected
three rows across its traversal. Absence cannot be inferred from the first page.

A native scalar diagnostic confirmed HTTPS, the exact app path, no fragment and
query keys in order: `api-version`, `%24filter`, `%24skiptoken`. The filter uses
`+` for spaces and `%27` for quotes. Encoding the decoded opaque cursor
reproduced the original; its encoded length was 304. No cursor value or row was
exposed.

A separate native Save rejected a constant Parse JSON schema with
`ActionSchemaNotSupported`: `pattern` and `patternProperties` are unsupported.
A constant schema using types, required members, enum and length bounds saved
and ran. Offline JSON-schema tests did not establish native support. Remove all
regex-dependent permission schemas, including assignment names and GUIDs.

**Decision:** add stateless, read-only `ValidateAppPermissionRead` to the existing
broker. Python validates bounded cumulative page content, identities and cursors.
The flow keeps three explicit HTTP slots, Makers writes, Management pacing,
durable sharing leases and reconciliation. This uses the existing API, connector,
gateway and authentication; it adds no service, network client or credential.

This keeps deterministic validation in directly testable Python instead of large
generated WDL character programs. It adds one internal operation and at most three
broker calls per observation; measure gateway latency during native acceptance.
Exclude this operation from the ordinary Power Apps operation allowlist.

### Read-only authorization and payload

Authenticate transport normally, run `authorize_person`, require current active
`users.manage`, then read one control-state snapshot. Require the exact stored
pending plan/revision and current target access revision. Its original users
command must belong to the authenticated actor and broker profile; configured
broker identity/tenant must still match. Select exactly one app resource in that
plan and derive app ID, tenant, environment and target principal from server state.

Use the existing `InvokeBroker` envelope and a strict payload:

| Field | Contract |
|---|---|
| `plan_id`, `revision` | Current stored plan UUIDs |
| `resource_environment` | `stage` or `prod`; selects that plan's app |
| `phase` | `before` or `after`; label, not authority |
| `observation_started_at` | UTC timestamp created immediately before page one |
| `pages` | Ordered list of one to three objects |
| `pages[].request_url` | Actual requested URL, at most 4,096 characters |
| `pages[].response_json` | Protected `string(body(HTTP_action))`; at most 250,000 UTF-8 bytes per page |

Cap combined page bodies at 750,000 UTF-8 bytes. Preserve the existing
1,100,000-character envelope limit, including serialized escaping and metadata.
Check actual serialized payload length in a protected flow action before invoking
the broker. Oversized content is incomplete. These are acceptance bounds, not
upstream HTTP response-size guarantees.

The operation requires **no lease or native-run fields**: it does not change state
or create durable permission evidence. A read-only native trial can call it through
the existing broker connection without impersonating the real broker flow. It must
not create/release a lease, reserve a permit, append audit events, persist raw pages,
issue HTTP, change membership or call `RecordSharingResult`.

The actual reconciliation flow still acquires its genuine native-bound lease
before reads. Only that generated branch may use fresh complete output with its
exact issued plan to reach writes or final recording. Submitted JSON or a validator
result alone is not proof of a native read. This preserves the trusted-flow
boundary; it does not attest to the origin of arbitrary supplied page content.

### Result contract and existing role rules

Return exactly `schema_version=1`, `plan_id`, `revision`, `resource_environment`,
`app_id`, `tenant_id`, `target_object_id`, `phase`, `observation_started_at`,
`expires_at`, `disposition`, `reason`, `page_count`, `row_count`, `next_url` and
`matching_assignments`. Server-derived UUID fields use canonical lowercase.
Validate the observation timestamp but echo its original string unchanged:
native `utcNow()` can contain seven fractional digits that Python would otherwise
truncate. `expires_at` may use normalized UTC format. The flow checks every binding
against its request and issued plan, normalizing UUID case for comparison.

| Disposition | Permitted output |
|---|---|
| `CONTINUE` | One validated canonical next URL; no target assignments |
| `COMPLETE` | Null next URL; zero or one sanitized target assignment |
| `INCOMPLETE` | Null next URL; no assignments; fixed reason only |

Authorization/binding failures use existing sanitized broker errors. Content
failures use fixed reasons such as `INVALID_PAGE`, `INVALID_CURSOR`,
`DUPLICATE_ASSIGNMENT`, `ROW_LIMIT`, `PAGE_LIMIT` and `DEADLINE_EXPIRED`.
These six reason literals are the complete validator reason enum; reason is null
for CONTINUE/COMPLETE. Payload/schema/authorization errors retain sanitized HTTP
errors. Failed broker/result parsing is also incomplete; never echo rejected
values. Map reasons to existing callback diagnostics: ROW_LIMIT to ROW_LIMIT,
PAGE_LIMIT to PAGINATED, and other content failures to FILTER_FAILED; transport
failure remains CALL_FAILED. Keep the existing resource-specific prefixes/suffixes
and do not expand SharingErrorCode merely to duplicate internal reasons.

The compact target projection retains only assignment ID/name, role name and
principal ID/type/tenant ID. Preserve current flow User/CanView rules, the pinned
deployment-Owner exception, edit eligibility and removal-ID selection. The Owner
pin is in reviewed flow bindings; do not invent a second backend owner setting.
Elevated or non-User targets remain unverified and cannot become verified absence.

### Exact one-form cursor grammar

The initial request keeps its documented `%20` filter spaces. Continuations use
this different, observed literal prefix, with the fixed generated app ID:

```text
https://api.powerapps.com/providers/Microsoft.PowerApps/apps/{fixed_app_id}/permissions?api-version=2017-06-01&%24filter=environment+eq+%27Default-9f5c0ace-0780-4b48-8c24-b08bb5149210%27&%24skiptoken=
```

Accept exactly this serialization. Perform a case-sensitive Python prefix check,
then validate only the remaining opaque suffix:

- Encoded length 1–2,048; full URI at most 4,096.
- Python `re.fullmatch` with `(?:[A-Za-z0-9._~-]|%[0-9A-F]{2})+`, plus the
  separate length bound. This regex never runs in native Parse JSON.
- `quote_from_bytes(unquote_to_bytes(suffix), safe="-._~") == suffix` using
  `urllib.parse`. Reject decoded control bytes and DEL; keep token bytes opaque.
- Reconstruct the URL from the fixed prefix and validated suffix. Never return
  an unvalidated upstream URL or decode/re-encode the whole URI.

The native canonicalization result supports this treatment. The conservative
ASCII/escape grammar must pass real traversal before release; a rejection requires
safe character-class evidence and narrow review, never exposure of the token.

The prefix fixes host, scheme, port absence, path, version, filter, key order and
uniqueness. Suffix validation excludes raw separators, fragments, whitespace and
backslashes; encoded delimiters remain inside the opaque query value. Canonical
round-trip rejects percent-encoded unreserved aliases and alternate escape case.

A present continuation field must be string or null. Absent/null/empty means none.
If both cursor fields are nonempty they must be identical. Require the first
request URL to equal the fixed initial route and each subsequent request URL to
equal its predecessor's validated continuation. Reject repeated cursors/routes,
a page following a terminal page, and any chain mismatch. A third page with
continuation is incomplete; never fetch a fourth.

The connection's base URL is supplementary enforcement. Microsoft states that
[endpoint filtering does not evaluate dynamic endpoints](https://learn.microsoft.com/en-us/power-platform/admin/connector-endpoint-filtering);
this design does not relax TAB policy if continuation expressions are prohibited.

### Page content and cumulative proof

Revalidate the whole supplied prefix on every call. Use Python JSON parsing with
duplicate-key rejection for supplied JSON text, bounded typed models and standard
UUID/regex validation. Do not coerce malformed values into an empty permission list.

Require every page to be an object with a value array and no error member,
including `error:null`. Validate all rows before returning a continuation:

- Required assignment ID/name and properties/principal objects. Roles are
  CanView/CanEdit/Owner; principal types are User/Group/Tenant.
- Name contains 1–128 ASCII letters/digits/underscore/dot/hyphen; reject exact
  dot and every double-dot sequence. ID equals the fixed app permission prefix
  plus name, with the existing 512-character cap.
- Principal ID and tenant have canonical 36-character hexadecimal UUID shape;
  normalize case for comparison and require the configured tenant. `UUID()`
  alone is insufficient because it accepts other spellings.
- Fewer than 1,000 cumulative rows. Reject duplicate normalized assignment IDs
  and principal IDs across all pages, even when other fields differ. Never
  deduplicate before counting.

Ignore bounded additional native fields without copying them into output. Do not
invent an optional row-type constraint: its native value was not established.
An empty intermediate page with a new cursor consumes a slot and is not terminal.
Only a valid prefix ending without continuation can return COMPLETE and no target.

### Minimum protected graph

For each of eight app-observation sites generate:

1. Protected start Compose, then fixed page-one HTTP.
2. Protected payload Compose, internal broker call and primitive-only result
   Parse JSON. Include the actual first URL and page body.
3. A sibling Page2 If gated on successful prerequisite actions, matching bindings,
   CONTINUE and an unexpired deadline. Fetch only the returned next URL, then
   validate cumulative pages one and two.
4. A sibling Page3 If applying the same checks to page two, then validating all
   three pages. No failure or incomplete predecessor can start it.
5. Protected terminal selection/result guard accepting only a COMPLETE slot with
   all required preceding HTTP/payload/broker/parser actions successful, correct
   bindings and time remaining. Then expose compact target rows to existing logic.

If expressions contain only necessary booleans, not raw rows or URLs. A successful
outer If does not prove its branch ran. Slots skipped after an earlier complete
page are optional; any required skipped/failed/timed-out action is incomplete.
Never fabricate an empty page on failure. Diagnostics may run after terminal
failure statuses but cannot enable writes.

Page3's outer If runs after the outer Page2 If, not a child in another container.
The first child uses an empty runAfter; its successors depend on siblings. Final
selection runs after outer Page3's terminal state and inspects required child
statuses explicitly. Microsoft permits nested-output references but restricts
[runAfter to the same control structure](https://learn.microsoft.com/en-us/azure/logic-apps/logic-apps-workflow-actions-triggers).

Retain exact issued-plan/held-lease branch checks and role safeguards before writes.
A new after-read starts with a new timestamp and page one; never reuse before-read
pages or results. Only complete fresh readback can verify presence/absence.
Incomplete readback remains pending and retains current unknown-outcome handling.

### Privacy, 90-second budget and limits

Protect each HTTP, payload, broker action, parser and downstream projection
explicitly. Microsoft supports secure connector settings, excludes variables/If,
and uses Secure Inputs for Compose/Parse JSON to hide outputs. Do not rely on
automatic downstream propagation. No cursor/row/ID variables or tracked properties;
raw pages stay in broker request memory and out of logs, errors and stored state.
[Run-history protection](https://learn.microsoft.com/en-us/azure/logic-apps/set-up-security-permissions)

Adopt **90 seconds per observation**, starting immediately before page one.
Backend validation rejects starts over five seconds in the future or older than
90 seconds, and returns start plus 90 seconds as expires_at. The flow rechecks
before continuations, terminal acceptance and immediately before any write.
A delayed response cannot revive an expired observation.

This bounds admission/freshness, not in-flight connector duration or the entire
multi-resource sharing flow. An active call may outlast expiry; later continuation
and mutation must then stop. Measure native latency rather than silently extending
the budget. Timeout never releases a durable lease or uncertain permit.

One observation has at most three HTTP GETs and three internal validation calls.
No loops, automatic pagination, retries or fourth-page fallback. The validator
itself issues no network requests.

The earlier source baseline has 265 actions and eight observation sites. Replace
its old five-action row validators. A nominal new site has a start, three
HTTP/payload/broker/parser groups, two sibling guards and terminal validation;
the actual generated count is mandatory. Enforce 500 actions, eight enclosing
containers, 80-character names and 8,192-character expressions. Preserve write
branch depth. Microsoft also documents 120-second synchronous request limits;
none of these guards cancels an active connector call.
[Platform limits](https://learn.microsoft.com/en-us/power-automate/limits-and-config)

### Implementation and release gates

1. Implement the pure validator and scoped broker operation; keep it out of the
   Canvas allowlist. Prove no control-state/audit/lease mutation or network access.
   Test wrong actor/profile/plan/revision/resource and superseded target state.
2. Cover one/two/three-page completion, malformed JSON/duplicate keys, all row and
   cross-page identity cases, 999/1,000 rows, body/envelope bounds, empty middle
   pages, both cursor fields, exact grammar, changed scope/host/path/query keys,
   repeated routes, final continuation, future starts and expired deadlines.
3. Regenerate without permission pattern/patternProperties. Test actual generated
   dependencies so failed GET/broker/parser, required skipped branches and expiry
   cannot reach Makers writes or verified readback. Count the whole graph and
   independently inspect secure settings.
4. Use the existing read-only native trial with normal TAB identity and a genuine
   current plan for Stage and Prod. Record only disposition, counts, elapsed time
   and fixed reasons. Verify masked history, terminal completion and cursor grammar;
   never forge a lease or broker-flow identity to run the diagnostic.
5. Independently review implementation and native evidence before broker import,
   then retain sharing, second-user, enforcement and both-app publication gates.
   Read-only acceptance alone is not successful sharing.

This local design does not claim revised broker/flows or unpublished Canvas
drafts have been deployed or accepted.
