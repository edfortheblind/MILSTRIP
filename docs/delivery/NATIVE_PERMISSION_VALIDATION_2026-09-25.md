# Native permission validation — September 25, 2026

**Read-only native validation accepted; reviewed brokers imported and On.** These
observations come from the existing unshared manual diagnostic flow and native
Studio UI. Sharing acceptance and publication of the updated apps remain pending.

## Verified read behavior

The fixed Stage permissions GET through HTTP with Microsoft Entra ID
(preauthorized) authenticates with normal TAB SSO. HTTP inputs and outputs are
protected. `json(string(body(...)))` reads the actual response content.

| Structural fact | Native result |
|---|---|
| First-page row count | 2 |
| Nonempty nextLink | true |
| Nonempty @odata.nextLink | false |
| Top-level error key | false |
| Continuation scheme | HTTPS |
| Continuation host/path | Exact expected API host and Stage app path |
| Ordered query keys | api-version, %24filter, %24skiptoken |
| Filter spaces / quotes | `+` / `%27` |
| Encoded cursor length in the sampled response | 304 characters |
| Encode(decode(cursor)) equals the encoded cursor | true |
| Fragment present | false |

The exact fixed continuation prefix is the app permissions path followed by:

```text
?api-version=2017-06-01&%24filter=environment+eq+%27{fixed_environment}%27&%24skiptoken=
```

The environment is substituted from fixed server configuration. No cursor value
was exposed. The first GET's `%20` filter spacing is accepted, but the service
serializes its continuation with `+`. The earlier complete host result of three
assignments was an aggregate and cannot establish first-page completeness.

The protected diagnostic Compose used deliberate fixed-label JSON parse failures
to expose only scalar structural facts through the action's error message.
Those intentional diagnostic failures are not failed HTTP authentication.

## Native schema capability

A constant synthetic Parse JSON probe with a string `pattern` was rejected at
Save with **ActionSchemaNotSupported**. The platform explicitly states that
`pattern` and `patternProperties` are unsupported when the workflow has
OpenApiConnection triggers/actions. Therefore the earlier single-page row
schemas could not be deployed as written. Offline JSON-schema tests did not prove
native compatibility.

Replacing the pattern with primitive `type`, `required`, `minLength`,
`maxLength` and `enum` constraints allowed Save. The constant valid payload
passed that action and reached the following diagnostic Compose. This confirms
acceptance of that valid probe; it does not prove every invalid case or other
JSON-schema keyword behaves as expected.

The revised design moves strict URI and permission-row validation into a pure
read-only operation in the existing authenticated broker. No new authentication
service or token export is involved. The flow retains bounded page requests,
protected history and the existing permission-mutation/lease gates. Backend and
generated source pass independent review and local tests. The bounded reader's
native acceptance is recorded below; full broker sharing acceptance remains pending.

## Native Canvas formula check

After resuming, Stage and Prod Studio App checker each displayed **no formula
errors** and exactly two formula warnings: the intentional literal predicates
on scrResults and scrHistory. No formula-error category was present.
Private screenshots are `.cred/stage-formula-check-continued.png` and
`.cred/prod-formula-check-continued.png`; the safe summary is
`.cred/native-formula-check-continued.json`.

The prior export's Parser count of one still has no diagnostic location or
message. It is not classified as a harmless artifact. The current native check
establishes no formula error in Studio, while full workflow/runtime acceptance
remains required. No Canvas source was changed or published by this check.

## Preserved state

Local readback after resume, before the trial: three active users, three pending users,
zero sharing leases, security enforcement false and runtime authority false.
The local API answers with HTTP401 when no credential is supplied. No new
permission grant or database/hostname cutover occurred during these probes.

## Reviewed implementation and connector import

The three-page implementation passed 322 reader/flow/package tests. Independent
review found and closed two defects: malformed compact permission replies could
be interpreted as absence, and an Admin could place their own membership into
pending by saving their existing role. Compact replies now require the expected
assignment/target/tenant/app binding; self-access changes fail before any write
and direct the caller to another Admin/Owner.

The existing custom connector received an enum-only update through the native
solution import. The portal reported import success. The update adds
InitializeRuntimeDraft, GetIntakeWorkflow and internal ValidateAppPermissionRead;
authentication, endpoints, connection parameters and policies are unchanged.
The import excluded workflows and Canvas apps. Automatic activation was disabled.
The current local API restarted successfully with the reviewed implementation;
an anonymous request to /api/v1/health returned HTTP401.

The rebuilt read-only diagnostic package was independently accepted for a native
trial. Both app observations exactly use the current production reader helper.
It includes one existing manual workflow, packaged Off, and three connection
references. The diagnostic contains no sharing mutation or lease operation.
Package SHA256: `53faa2c262ed5f7ea76c9798e04f8b44741af1d19ca0c3dff6810b521c500293`.
Native import completed with the portal warning that the original workflow was
deactivated and replaced. On details refresh, its actual state was On despite
the package Off flag and disabled automatic activation. The operator explicitly
turned this manual diagnostic Off and verified the native Off status before
further acceptance. Package flags alone are not proof of runtime state.
Subsequent native graph verification and traversal acceptance are recorded below.

The complete final local suite passed **1,003 tests, none skipped**, with two
upstream warnings in 214.68 seconds, including approved localhost PostgreSQL
integration. This is local evidence, not native app publication acceptance.

## Native bounded traversal acceptance

The updated read-only diagnostic succeeded for **both Stage and Prod**. Its final
assertion, `Both_apps_complete_two_pages_three_rows`, reached **Succeeded** and
required each app to have two pages, three cumulative rows, validated terminal
completion and no diagnostic failure. Native Code view matched the reviewed
assertion expression, runAfter dependencies and secure settings exactly.
Both final inputs and outputs displayed "Content not shown due to security
configuration." The checked native HTTP action also retained protected inputs
and outputs, GET-only access, the fixed app/environment URL and no retry.

The native test reused a previous manual trigger through Power Automate's
**Automatically** option with a recently used trigger. The normal Run panel
requested location services due to the existing default manual-trigger schema;
location permission was not granted. The test used the current imported graph
and normal TAB directory/connector identities, with the genuine pending plan.
It performed no sharing mutation or lease operation.

Client tracking ID: `08584112488577480824387761858CU12`.
The control file digest was unchanged across the trial: three active users,
three pending users, zero leases, security enforcement false and runtime
activation false. This establishes bounded native read acceptance only.
Full broker workflow acceptance, membership reconciliation, second-user identity,
host enforcement, configuration activation, intake workflow acceptance and
publication remain pending.

Private native evidence: `.cred/native-permission-traversal-acceptance.json`,
`.cred/native-permission-final-assertion-code.json`,
`.cred/native-permission-final-assertion.png` and
`.cred/native-diagnostic-stage-http-code.json`.

The native run history reports **14 seconds total**. Independent review accepted
its safe evidence and unchanged control digest. The manual diagnostic was then
explicitly turned Off and the native Turn on action was verified. The existing
broker update and rollback packages also passed independent review. Subsequent
native runtime-state checks are recorded below.

## Broker import and activation verified

Both existing Stage and Prod brokers were explicitly turned Off and their native
Off states verified before import. Import of the reviewed two-flow package
completed successfully. Connection review listed seven existing references,
zero required updates and seven optional updates. The import reused those
references without rebinding; automatic activation remained unchecked.

Independent comparison of the resulting native export matched each broker's
trigger and all 417 actions to its reviewed definition. Differences were limited
to expected native connection serialization. All six Canvas assets and their
metadata were unchanged. The connector comparison showed only the three
authorized operation-enum additions documented above.

Both brokers were verified Off after import, then explicitly activated and
verified On in the native UI. The manual diagnostic remains verified Off.
These checks establish deployed graph and runtime state, not completed sharing.
Full broker workflow acceptance, membership reconciliation, second-user identity,
host enforcement, configuration activation, intake workflow acceptance and Canvas
publication remain pending. Guide 1.5.0 remains published.
