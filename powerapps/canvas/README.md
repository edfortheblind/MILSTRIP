# MILSTRIP Stage and Prod canvas apps

**Current status: September 24, 2026:** both apps are published in the existing
MILSTRIP solution and organization Default environment. Prod's runtime profile
is disabled until its independent database target is selected.

The standalone Prod player requested a Power Apps plan for the current account.
Licensing remains with IT, as the owner directed; no trial was started. Studio
Preview checks passed, but standalone player acceptance is still blocked.

| App | App ID | Fixed App.Formulas source | Runtime |
|---|---|---|---|
| MILSTRIP Stage | `7f1b64d0-d51a-4ec8-84ad-2b18fe8c2f82` | [app-environment.stage.fx](app-environment.stage.fx) | Existing local PostgreSQL Stage |
| MILSTRIP Prod | `0aa02d8b-c7fa-42cc-87e8-6d287bd4c897` | [app-environment.prod.fx](app-environment.prod.fx) | Disabled; target pending |

The [deployment manifest](deployment-manifest.json) records the source/settings
mapping. `app-environment.fx` remains the equivalent Stage source for existing
references. The two apps reuse MILSTRIP Local Dev API and MILSTRIP-DEV-LAPTOP,
with separate credential-bound connections. API version is **0.4.0**.

## Apply the correct source variant

1. Verify the app ID and retain a backup before editing. Preserve existing work
   and the original Screen1 scaffold where present.
2. Use that app's connection to the existing connector. The data-source identifier
   remains `MILSTRIPLocalDevAPI`; changing its display name is not environment
   isolation. Verify its authenticated `GetHealth` response.
3. Set **App.Formulas** from the matching Stage or Prod file above. Keep
   **App.StartScreen** set to `scrIntake`. Do not use a mutable environment
   variable or give operators a destination selector.
4. Apply the four matching `*.controls.yaml` files to `scrIntake`, `scrResults`,
   `scrReview` and `scrHistory`. Use the existing 1366 x 768 tablet layout and
   `milstrip-app` media asset. Update populated screens without creating duplicate
   controls.
5. Apply [environment-check.fx](environment-check.fx) to **OnVisible on all four
   screens**. The **Check connection** button runs the same check with a busy
   indicator. It requires both the expected environment and `ready=true`.
6. Preserve formula-level error handling. Do not add startup resets that discard
   source input or unresolved review commands.
7. Resolve formula errors, save and test the intended app, then publish its
   verified version. Recheck the player. Updating Stage does not automatically
   promote its canvas version or connection binding to Prod.

Microsoft documents the [code-view paste workflow](https://learn.microsoft.com/en-us/power-apps/maker/canvas-apps/code-view)
and [v3 source schema](https://github.com/microsoft/PowerApps-Tooling/blob/master/schemas/pa-yaml/v3.0/pa.schema.yaml).
Static source validation does not verify connector binding or Power Fx execution;
Studio/player checks are still required.

## Current behavior

- Every screen checks the fixed environment. Studio Preview verified mismatch
  blocking in Stage and disabled-profile blocking in Prod. A successful Preview
  does not establish licensed standalone player access.
- Intake preserves pasted text. An uncertain submission blocks another submit:
  reconcile its source ID in recent requests before allowing a new submission.
  Intake POST is not idempotent.
- Results keep validation and review separate. The persistent receipt shows
  Request ID, time and **Validation at intake** counts. Reopened requests use
  matching details; they do not borrow counts from another request or one page.
- Canonical values are read-only and retain all 80 characters, including trailing
  spaces. Invalid records cannot receive an APPROVED review.
- Review commands retain one UUID and frozen payload while the outcome is
  unknown. **Retry same command** reuses them. A 409 requires **Reload after
  conflict**, then a decision based on the latest version.
- History shows request-scoped event metadata. Its actor is the shared API
  identity; individual-user API authorization is not implemented.

Input and pending commands exist only while the app remains open. After a browser
restart, reconcile recent requests and history before resubmitting. There is no
legacy order write, CSV export or downstream receipt in either app.

## Verification and retention

The [September 24 retained test](../../docs/delivery/RETAINED_RUNTIME_TEST_2026-09-24.md)
passed intake, mixed results, valid approval, invalid-record rejection and history
through the existing app/gateway/API/PostgreSQL path. Its request
`1d0c784d-c3bf-495c-928c-0b66687a58a4` must remain in Stage.

Stage publication testing retained request
`ff3f3cb5-04f5-4135-af74-f8db41962673`. Its four app-only captures are used in the
illustrated SOP. The current Stage and Prod formula checks reported zero errors
and two pre-existing literal-predicate warnings for empty galleries.
The [publication query](../../db/queries/retained_stage_publication_2026-09-24.sql)
reads its retained database results without changing them.

Published `.msapp` exports are retained in `%LOCALAPPDATA%\MILSTRIP\backups\`.
The [publication evidence](../../docs/delivery/RUNTIME_PROFILES_2026-09-24.md)
records their filenames and SHA-256 hashes. Exported source confirms each app's
fixed environment, guards on all four screens and distinct connection references.

Continue acceptance for exact review retry, two-client conflict, all pagination,
accessibility and gateway/API outage recovery. Do not turn existing evidence into
an assertion that every UI failure path or a live SQL Server destination passed.

Use the [administrator SOP](../../docs/RUNTIME_CONFIGURATION.md) for database
changes and [tenant SOP](../../sop/powerapps-setup.md) for connections/publication.
Both apps share the same backend; a backend restart or code deployment affects
both even though their databases and canvas versions are separate.
