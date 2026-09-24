# TAB: MILSTRIP sign-in and connection recovery

**For:** Claude Furry, Mike Thompson and TAB System Administration

**Date:** September 24, 2026

**Current IT action: none.** TAB's existing Microsoft Entra sign-in and the
required OAuth connections work. The remaining app-sharing acceptance issue is
being investigated by the developer; it is not an established SSO or policy
failure.

## Current state

- Both broker flows are Started and use the existing MILSTRIP solution, Default
  environment and gateway. Keep their current connection references.
- The published four-screen apps still use a shared API identity. Stage is
  healthy; Prod opens with its database disabled. Individual-user enforcement
  has not been activated.
- Both six-screen administration drafts are saved and verified but unpublished.
  The new membership store has Claude and Mike as active protected Owners and Ed
  as active Admin; Kristen, Thomas and Shawn remain pending. These roles do not
  establish role isolation in the currently published apps.
- The final paginated permission-read trial stalled and was canceled. User-sharing
  acceptance remains incomplete and rollout is withheld. Recovery requires
  developer review; do not retry, reset its retained state, recreate connections
  or change TAB policy to bypass this result.

Application Owner grants MILSTRIP permissions only. It does not grant Entra
administration, app editing or platform ownership. Prod database activation
requires a separate owner decision.

## Recover a failed connection

Use this procedure only if a connection later becomes unauthenticated.

1. Open [Power Automate Connections](https://make.powerautomate.com/environments/Default-9f5c0ace-0780-4b48-8c24-b08bb5149210/connections/available/shared_flowmanagement)
   in TAB's work session. Select the existing Default environment for Travis
   Association for the Blind. Inspect **MILSTRIP Management SSO**, connection ID
   `07c12ec437fa43e289082155a221a981`.
2. Repair or reauthorize the existing connection from this page. The successful
   setup used **Power Automate Management > Microsoft Entra ID Integrated / First
   Party** with Ed's deployment account. If a replacement is necessary, coordinate
   its account, ownership and references with the developer before creating it.
   Reuse the existing environment, solution and gateway.
3. Confirm **Connected**. Have the developer run read-only **Get Flow** checks
   against both resources below. This check must not trigger the broker or change
   anyone's permissions.
4. In **Solutions > MILSTRIP > Connection references**, verify
   `tab_milstripmanagement` selects the working connection. Record the connection
   ID, account and successful read checks for the handoff.

| Existing flow | ID |
|---|---|
| MILSTRIP Stage Broker | `04d6229f-5ab8-f111-aaac-7ced8d6f317c` |
| MILSTRIP Prod Broker | `fbe87a93-68ef-4efb-88db-facc21c125f6` |

The Connections page succeeded after two earlier flow-editor attempts failed.
Their cause was not established; do not assume a tenant-policy restriction.
See Microsoft's [connection instructions](https://learn.microsoft.com/en-us/power-automate/add-manage-connections),
[Management authentication options](https://learn.microsoft.com/en-us/connectors/flowmanagement/#creating-a-connection)
and [Get Flow reference](https://learn.microsoft.com/en-us/connectors/flowmanagement/#get-flow).

## If sign-in still fails

Record the attempt's time/time zone, account, environment, error and correlation
ID. In **Entra ID > Monitoring & health > Sign-in logs**, find the matching event
and inspect its failure reason and policy evaluation. Use that evidence to route
any consent or policy request through TAB's normal approval process, or retain
the diagnostic IDs for Microsoft support. Never include passwords, tokens or
authorization headers in the handoff. Follow Microsoft's
[sign-in troubleshooting procedure](https://learn.microsoft.com/en-us/entra/identity/monitoring-health/howto-troubleshoot-sign-in-errors).

No new identity provider or SSO bypass is part of this deployment.

## Preserve these connection settings

| Purpose | Required setting |
|---|---|
| Office 365 Users: Get my profile (V2) | Provided by run-only user; identifies the caller |
| Directory lookup, Makers and Management | Private embedded deployment connections |
| API broker | Private embedded gateway connection, distinct for Stage and Prod |

Ordinary users receive app **CanView** and flow **run-only** rights. Do not share
the embedded connections or grant flow editing. See Microsoft's
[run-only connection settings](https://learn.microsoft.com/en-us/power-automate/create-team-flows).
Connection recovery does not authorize security cutover, app publication or
production database changes.

The developer owns sharing reconciliation, second-user/role acceptance,
configuration Apply and recovery checks, security activation and publication.
Detailed results, retained command IDs, test counts and remaining limits belong
in the [deployment status](delivery/IDENTITY_ADMIN_STATUS_2026-09-24.md).
Database changes follow the [administration SOP](RUNTIME_CONFIGURATION.md).

<details>
<summary>Recorded protection evidence</summary>

Metadata-only checks on September 24 Stage runs
`08584113190214236444505960035CU02` (22:11:04 UTC) and
`08584113190102759476565110458CU01` (22:11:15 UTC) verified secure inputs/outputs
without opening protected content. They do not establish second-user acceptance.

</details>
