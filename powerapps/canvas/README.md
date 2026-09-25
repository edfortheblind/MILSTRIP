# MILSTRIP Stage and Prod canvas apps

**September 25, 2026: published for limited acceptance.** Stage version **16**
and Prod version **6** are Live in the existing MILSTRIP solution and Default
environment. Both use six screens and their matching updated broker. The existing
six configured memberships are active. Broker-only enforcement is active; old
four-screen direct-connector players cannot use the API. Prod's database remains
disabled. See the [native acceptance record](../../docs/delivery/NATIVE_PILOT_ACCEPTANCE_2026-09-25.md)
for player evidence and remaining multi-user checks. Licensing evidence applies
only to the verified administrator's sessions.

| App | App ID | Current source | Runtime |
|---|---|---|---|
| MILSTRIP Stage | `7f1b64d0-d51a-4ec8-84ad-2b18fe8c2f82` | [broker/stage](broker/stage) | Existing local PostgreSQL Stage |
| MILSTRIP Prod | `0aa02d8b-c7fa-42cc-87e8-6d287bd4c897` | [broker/prod](broker/prod) | Disabled; target pending |

The [deployment manifest](deployment-manifest.json) records actual live versions.
The generated [broker manifest](broker/manifest.json) is a source template, not a
live-deployment assertion. Legacy top-level `app-environment.*.fx`,
`environment-check.fx` and four-screen controls remain historical source; do not
apply them over the broker apps or restore direct shared API access.

## Apply the current source

1. Verify the existing app ID and retain a native export before editing. Bind only
   the matching `MILSTRIPStageBroker` or `MILSTRIPProdBroker` Power Apps V2 flow.
2. Set App.Formulas and App.OnStart from the matching broker directory. Keep
   App.StartScreen `scrIntake`; operators do not select environments.
3. Apply all six `*.controls.yaml` screens and `screen-events.json`. Preserve the
   existing layout/media and formula-level error handling. Do not create duplicate
   controls or reset unresolved submissions/review commands.
4. After flow changes, refresh or remove/readd that same flow as required by Studio,
   save, and verify the exported binding and executable formulas. Compile and
   exercise native workflows; static generation checks alone do not prove execution.
5. Follow the [pilot publication order](../../docs/delivery/PILOT_PUBLISH_ORDER_2026-09-25.md).
   Publish only the accepted app, then verify its actual Live version and standalone
   player. Stage publication does not promote Prod automatically. Shared users may
   need the player's Refresh action to load the new version.

Microsoft documents [code-view paste](https://learn.microsoft.com/en-us/power-apps/maker/canvas-apps/code-view)
and [flow metadata updates](https://learn.microsoft.com/en-us/troubleshoot/power-platform/power-apps/connections/best-practices-when-updating-a-flow).
Office 365 Users must use each run-only user's own connection. Private broker and
sharing connections are not the authenticated human identity.

## Behavior and acceptance limits

- TAB sign-in and the active app membership authorize the caller. Configuration
  and user administration are restricted to Admin/Owner capabilities.
- Save/Test/Apply and explicit guarded Initialize are in Configuration. Saved
  credentials are never redisplayed. Provider detection follows the connection
  string; schema/data migration remains separate from a connection change.
- Every intake record needs a final review before another intake. Normalized
  duplicates are blocked for two hours; Admin/Owner can provide an audited reason
  to override duplicates, but cannot override unfinished review.
- Intake receipts retain request ID, time and validation counts. Uncertain
  submission preserves text/source ID and blocks resubmission; Resume / new intake
  reconciles the exact source receipt. Intake POST is not idempotent.
- Results separate validation from review. Canonical values retain 80 characters;
  invalid records cannot be approved. A review retry reuses its frozen command and
  expected version. History records the verified human actor.
- Native configuration, final-review locking, normalized duplicate blocking,
  audited override and actual configuration/review recovery passed for the
  administrator. Intake-specific submission uncertainty, second-user identity,
  role/denial/revocation/concurrent-session checks and existing accessibility/parser
  diagnostics remain acceptance items. Publication does not close those items.

Input and pending commands exist only while the app is open. After a browser
restart, reconcile receipts/history before resubmitting. Delivery to the legacy
pipeline is not connected. No Azure SQL database or always-on hostname has been
activated; the local API/gateway remain required until the hosting roadmap is done.

## Evidence and retention

The [September 24 retained test](../../docs/delivery/RETAINED_RUNTIME_TEST_2026-09-24.md)
and [historical publication evidence](../../docs/delivery/RUNTIME_PROFILES_2026-09-24.md)
remain valid historical records; their old licensing/source details are not current
deployment state. Preserve their database rows and the September 25 synthetic
acceptance intakes, reviews and audits. Current private exports and hashes are
recorded in the native acceptance evidence; no secrets or native screenshots belong
in the public guide.

Use the [administrator SOP](../../docs/RUNTIME_CONFIGURATION.md),
[tenant SOP](../../sop/powerapps-setup.md) and
[network roadmap](../../docs/delivery/INTAKE_NETWORK_ROADMAP_2026-09-25.md).
Both apps share one API; its restart affects both even though database profiles,
broker flows and Canvas versions are separate.
