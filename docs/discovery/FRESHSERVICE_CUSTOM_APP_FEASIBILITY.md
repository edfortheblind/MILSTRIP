# Freshservice Custom App — Parallel Feasibility Research

**Date:** 2026-08-18  
**Status:** DISCOVERY ONLY — no architecture, scope, vendor, or release decision  
**Owner:** Ed Lopez (HOC)  
**Track:** Parallel to the approved MILSTRIP roadmap; does not replace or delay
Phase 2A unless the HOC later approves a change

## 1. Executive finding

A tenant-private Freshservice Custom App is a technically credible future
presentation and intake channel for MILSTRIP. Freshworks officially supports:

- Custom Apps that are private to one customer's selected Freshservice account;
- a `full_page_app` launched from the left navigation;
- ticket-detail placements including `ticket_sidebar`,
  `ticket_requester_info`, `ticket_top_navigation`, and background execution;
- New Ticket placements;
- front-end, serverless, and combined full-stack/SMI applications; and
- authenticated HTTPS calls to external services through request templates.

This finding establishes **feasibility, not suitability or authorization**.
The tenant edition, installation scope, agent visibility, security review,
network path, data handling, vendor support, and commercial terms must be
confirmed with the Freshservice administrator and Freshworks.

The most important correction to the initial hypothesis is that App SDK 2.3
is being deprecated. Any spike should target **App SDK 3.0 and the current
FDK**, subject to confirmation against the tenant's product variant. A Custom
App's packaged HTML is rendered by Freshservice in an iframe. Embedding an
arbitrary intranet page is not the documented integration boundary and would
also face browser framing policy, TLS, authentication, and network reachability
constraints.

## 2. What official documentation confirms

| Claim | Finding | Confidence |
|---|---|---|
| Private tenant app | A Custom App is private to the customer/product account selected during submission. It can be uploaded, tested in the production tenant, versioned, and published without becoming a public Marketplace app. | Confirmed |
| Full-page UI | `full_page_app` adds an icon to the left navigation and renders the app over the viewport. Only one active app can occupy that placeholder. | Confirmed |
| Ticket-context UI | The `service_ticket` module supports ticket sidebar/requester/conversation/top-navigation/background placements and New Ticket placements. | Confirmed |
| App isolation | The app's packaged page is rendered in an iframe and has constrained access to the host product; supported SDK interfaces bridge that boundary. | Confirmed |
| Freshservice context | At ticket locations, SDK data methods can retrieve the current ticket/requester context, subject to product and user permissions. | Confirmed |
| Back end | The platform supports serverless event handlers and Server Method Invocation (SMI) from the app front end. | Confirmed |
| External API calls | Request templates proxy HTTPS calls, can inject secure installation parameters into headers, avoid browser CORS dependence, and provide region-specific origin IPs for allow-listing. | Confirmed |
| Installation scope | Current manifests can declare account and/or workspace installation. Visibility and event/data scope differ: account UI is generally visible to all agents; workspace UI is limited to agents with that workspace access. | Confirmed, tenant applicability must be checked |
| Mobile | Freshservice product apps are documented as web apps, not mobile apps. | Confirmed |

## 3. Platform constraints that affect MILSTRIP

These are current documented platform limits, not capacity targets:

- request method: 50 requests/minute per app installation, normally 15-second
  execution, extendable in defined increments to 30 seconds;
- request/SMI payload: 100 KB; request response: 6 MB;
- SMI: 50 invocations/minute and normally 20-second execution;
- external events: 250 requests/minute per installation and 100 KB payload;
- packed app: 5 MB, with 2 MB maximum for an individual app file;
- Custom Apps: 25 per account by default; and
- platform storage has separate quotas and must not be assumed to be a durable
  operational audit database.

These limits appear adequate for interactive MILSTRIP review, but the meeting
must confirm whether limits, regions, and extensions differ for this tenant.
The app must handle rate limiting, timeout, retry safety, and unknown outcomes.

## 4. Candidate architectures

### A. Self-contained Custom App

```text
Freshservice ticket/full page
        |
        v
Custom App UI + TypeScript MILSTRIP core
        |
        +--> ticket context through Freshworks SDK
        +--> result shown for human review
```

The deterministic parser is ported to TypeScript and bundled with the Custom
App. No MILSTRIP payload leaves Freshservice/browser processing for analysis.

**Advantages:** least infrastructure; works naturally in ticket context; no
intranet reachability dependency.  
**Costs/risks:** a third implementation must maintain golden parity with Python
and C#; browser/runtime limitations; Freshservice release lifecycle and UI
dependency; no assumption of durable audit storage or Rainbow delivery.

### B. Thin Custom App plus authenticated HTTPS MILSTRIP API

```text
Freshservice Custom App
        |
        | HTTPS, authenticated, bounded request
        v
MILSTRIP API / gateway
        |
        +--> deterministic engine
        +--> future application DB / Rainbow adapters (separate gates)
```

This is the appropriate pattern if one canonical server-side engine is needed.
Freshworks request templates can protect credentials and originate calls from
documented regional IP addresses.

**Advantages:** one centrally governed engine; easier shared audit/versioning;
future integrations remain replaceable.  
**Costs/risks:** hosting, identity, availability, monitoring, data residency,
incident response, and vendor-to-enterprise network ingress become production
responsibilities. A service reachable only at an RFC1918/private LAN address is
not directly reachable by Freshworks cloud. IT would need an approved HTTPS
ingress pattern (for example an API gateway/reverse proxy with strong workload
authentication and narrow routing), not exposure of SQL or the whole intranet
application.

### C. Ticket-assisted handoff to the Windows app

Freshservice supplies ticket context or a deliberate copy/export, while the
accepted Windows application remains the analysis UI.

**Advantages:** preserves the existing C# investment and endpoint-local
processing.  
**Costs/risks:** context switching and duplicate user interaction; browser to
native launch/deep-link mechanisms add endpoint deployment and security work.

## 5. Preliminary recommendation

Do **not** select an architecture at the vendor meeting. Run a bounded,
non-production feasibility spike only after the tenant facts below are
confirmed.

For the first spike, prefer **Architecture A in a ticket sidebar**, using
synthetic MILSTRIP data and only parse/analyze/review behavior. It tests the
highest-value Freshservice proposition—using the current ticket context—without
creating a new externally reachable service or changing the Rainbow boundary.
Require the same golden and failure fixtures used by the Python/C# cores.

Evaluate `full_page_app` as a second placement, not the default assumption.
Full-page is suitable for a queue/batch workspace; ticket sidebar is better for
one-ticket-at-a-time intake. If parity, package constraints, or maintainability
make a third parser implementation unattractive, then evaluate Architecture B
through a formal security and network design gate.

The spike must not write tickets, export the 76-field file, call Rainbow, query
SQL, or process real operational data.

## 6. Security and privacy boundary

- Use App SDK interfaces and request templates; do not place API keys or tokens
  in browser-readable code or ordinary installation parameters.
- Any external middleware endpoint must be authenticated. IP allow-listing is
  defense in depth, not authentication.
- Require TLS with normal certificate validation; no bypasses or private
  certificate exceptions without IT design approval.
- Minimize payloads to the ticket fields/MILSTRIP text actually required.
- Define whether descriptions can contain controlled operational information,
  personal data, attachments, or HTML; sanitize output and never execute ticket
  markup.
- Do not log ticket bodies, MILSTRIP records, credentials, personal data, or
  external API authorization headers.
- Define retention, deletion-on-uninstall, region/data residency, subprocessor,
  support-access, backup, and breach-notification behavior before real data.
- Preserve the existing distinction between parsed, reviewed, locally exported,
  transfer attempted, and Rainbow-confirmed states.
- A Freshservice UI does not authorize direct SQL or Rainbow access.

## 7. Questions for the sysadmin and Freshservice meeting

### Tenant and commercial

1. What exact Freshservice product, plan/SKU, region, account age, and workspace
   model does this tenant use?
2. Is **Build your own apps / Custom Apps** enabled in this subscription, and
   is there any add-on, developer-seat, app-count, or usage cost?
3. Who can create, upload, test, publish, roll back, disable, and uninstall a
   Custom App? Is separation of duties available?
4. Can a Custom App be limited to the Travis/3PL workspace and a specific agent
   group, or does UI visibility extend to every agent with workspace access?
5. What vendor support/SLA applies to private Custom Apps and App SDK changes?

### Platform and lifecycle

6. Confirm App SDK 3.0, current FDK/Node versions, deprecation dates, and the
   modules/placeholders supported by this tenant.
7. Confirm `ticket_sidebar` and `full_page_app` availability and the one-active-
   app limitation for full-page placement.
8. What validation or review does Freshworks perform before a private version
   can be tested and published? Is there a tenant sandbox/UAT account?
9. What are the supported promotion, rollback, audit-log, and emergency-disable
   procedures? Can versions differ by workspace?
10. Are there release windows or automatic platform changes that can break an
    installed Custom App? What advance notice is provided?

### Identity, authorization, and audit

11. Which logged-in agent identity, role, group, ticket scope, and workspace
    attributes are reliably available to the app?
12. Can Freshservice enforce app access by group/role beyond workspace scope,
    or must the app perform its own authorization?
13. What OAuth/workload-identity options are supported for an external API?
    Avoid tenant-wide personal API keys.
14. Are installation, configuration, app invocation, external requests, and
    ticket mutations available in tenant audit logs? What is their retention?

### Networking and data governance

15. From which region-specific Freshworks IPs will request-method calls
    originate for this tenant, and how are IP changes communicated?
16. Does Freshworks support private connectivity to customer networks, or only
    Internet-reachable HTTPS endpoints? Ask explicitly about VPN/private link;
    do not assume it exists.
17. Can the request method use mutual TLS or a managed OAuth client credential?
    Where are client secrets/certificates stored and rotated?
18. Where do app execution, object/entity storage, logs, backups, and support
    access reside? What data residency and deletion guarantees apply?
19. Can platform logs capture request bodies or headers? How are sensitive
    values redacted, accessed, exported, and deleted?
20. Confirm current rate limits, payload limits, timeouts, availability, and
    whether contracted increases carry cost.

### MILSTRIP workflow

21. Can the app retrieve the complete ticket description safely in the actual
    email-to-ticket format, including HTML/plain text behavior and truncation?
22. Are ticket conversations and attachments needed, and what malware scanning
    and file-size/type behavior applies? Initial recommendation: exclude them.
23. Can the app add a private note or update custom fields only after explicit
    operator confirmation? Which permissions and audit events result?
24. Can synthetic test tickets be isolated from production automation and
    notifications?

## 8. Proposed spike and exit criteria

### Inputs required before starting

- written answers to Questions 1–10 and 15–16;
- a non-production tenant/workspace or approved synthetic test procedure;
- named tenant admin, security reviewer, and business tester;
- confirmation that no real operational data is used; and
- HOC authorization for the spike scope.

### Spike scope

1. Package a minimal App SDK 3.0 Custom App.
2. Render it in `ticket_sidebar`; optionally render the same component as
   `full_page_app` for comparison.
3. Read only synthetic ticket context through the SDK.
4. Run an in-browser deterministic parser proof using shared sanitized golden
   fixtures.
5. Demonstrate clear `VALID`, `REQUIRES_REVIEW`, and `REJECTED` states.
6. Validate install, version update, rollback/disable, and uninstall.
7. Record effective user/workspace visibility and available audit evidence.

### Exit criteria

- all existing golden/failure cases selected for the spike have byte-exact
  canonical parity;
- no network, ticket mutation, persistence, telemetry, database, export, or
  Rainbow behavior exists;
- access and visibility match the approved test group;
- package validation passes and lifecycle evidence is captured;
- security review identifies no unowned data flow; and
- HOC receives an evidence-based go/no-go recommendation among A, B, and C.

Failure to meet these criteria means the Freshservice option remains deferred;
it does not invalidate the Windows application.

## 9. Decision gates after the spike

1. **Channel gate:** Freshservice app, Windows app, or both.
2. **Engine gate:** TypeScript port versus authenticated shared API.
3. **Data gate:** exact ticket fields and whether any payload may leave
   Freshservice.
4. **Identity gate:** user and workload authentication/authorization model.
5. **Operations gate:** ownership, monitoring, support, rollback, retention,
   and cost.
6. **Integration gate:** ticket mutations, 76-field export, Rainbow, and
   database access remain separate future approvals.

No ADR should be accepted until these gates have evidence and an explicit HOC
decision.

## 10. Official sources reviewed

- [Custom App submission and tenant-private publishing](https://developers.freshworks.com/docs/app-sdk/v2.3/freshservice/app-submission-process/custom-apps/)
  — the available detailed custom-submission page is under the v2.3 path; its
  workflow is consistent with the current v3 submission overview, but must be
  reconfirmed for this tenant.
- [App SDK 3.0 Freshservice submission overview](https://developers.freshworks.com/docs/app-sdk/v3.0/service_ticket/app-submission-process/)
- [App SDK 3.0 Freshservice ticket placements](https://developers.freshworks.com/docs/app-sdk/v3.0/service_ticket/front-end-apps/placeholders/)
- [App SDK 3.0 common/full-page placements](https://developers.freshworks.com/docs/app-sdk/v3.0/common/front-end-apps/placeholders/)
- [App SDK 3.0 manifest and iframe rendering](https://developers.freshworks.com/docs/app-sdk/v3.0/common/front-end-apps/app-manifest/)
- [Freshservice ticket-context data method](https://developers.freshworks.com/docs/app-sdk/v3.0/service_ticket/front-end-apps/data-method/)
- [Secure external HTTP request method](https://developers.freshworks.com/docs/app-sdk/v3.0/service_resource/advanced-interfaces/request-method/)
- [Server Method Invocation](https://developers.freshworks.com/docs/app-sdk/v3.0/common/serverless-apps/server-method-invocation/)
- [Platform rate limits and constraints](https://developers.freshworks.com/docs/app-sdk/v3.0/deal/rate-limits-and-constraints/)
- [Freshservice app installation scope and visibility](https://support.freshservice.com/support/solutions/articles/50000011810-app-installation-types-in-freshservice)
- [Developer platform code/security guidelines](https://developers.freshworks.com/docs/app-sdk/v3.0/support_company/app-development-guidelines/code-guidelines/)
- [App SDK 3.0 changelog/what's new](https://developers.freshworks.com/docs/app-sdk/v3.0/custom_module/whats-new/)

## 11. Evidence limitations

- Documentation is generic across Freshservice variants; tenant-specific
  product, plan, account age, workspace configuration, and enabled features
  were not available.
- Public documentation did not establish the tenant's price, private-network
  connectivity, internal approval flow, or contracted support obligations.
- No tenant access, FDK prototype, API call, payload, or real ticket was used.
- The recommendation is therefore suitable for meeting preparation and a
  controlled spike proposal, not implementation authorization.
