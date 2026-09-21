# PostgreSQL Hosting Design

**Project:** MILSTRIP Intake Automation  
**Date:** 2026-09-21  
**Status:** Initial design with deployment placeholders; no hosting decision made

## 1. Design objective

The application must work with PostgreSQL hosted either:

1. on-premises inside the TAB network; or
2. on an Azure virtual machine (Azure VM).

The Power Apps canvas app must not depend on which option is selected. It calls
the application API, and only the API owns PostgreSQL connectivity. This keeps
database credentials, schema details and network routing out of Power Apps.

```text
Power Apps
   |
   | Entra/AD FS SSO + HTTPS custom connector
   v
MILSTRIP API
   |
   | PostgreSQL driver, TLS, pooling, migrations
   v
PostgreSQL: [TAB network] OR [Azure VM]
```

## 2. Common logical contract

Both hosting options must provide the same:

- PostgreSQL major-version compatibility agreed during implementation;
- `milstrip_app` application schema;
- DEV, TEST and PROD separation;
- migration mechanism owned by the application;
- roles for runtime read/write, migration and read-only support;
- TLS certificate validation, connection timeout and pool limits;
- point-in-time recovery or an approved equivalent backup strategy;
- restore test evidence;
- audit trail for state transitions without secrets or unnecessary raw payload;
- private connectivity from the API to the database;
- monitoring for availability, storage, connections, failed logins and backups.

The API must expose the same DTOs and state transitions regardless of the
database location. No Power Apps formula may contain a database hostname,
database role, SQL query or credential.

## 3. Option A: PostgreSQL inside the TAB network

### TAB topology

```text
Power Apps cloud
      |
      | HTTPS through approved API ingress/gateway
      v
API host [location TBD]
      |
      | private route / firewall allowlist
      v
PostgreSQL server in TAB network
      |
      +--> optional restricted legacy reference connection
```

### TAB required decisions

- Where the API runs: TAB network, Azure, or another approved host.
- Whether an on-premises data gateway, VPN, ExpressRoute or private API ingress
  is required for the Power Platform connection.
- Firewall source and destination rules for the API and administrator access.
- DNS, certificate authority and certificate rotation ownership.
- PostgreSQL server ownership, patch schedule, high availability and backups.
- Whether the API may reach legacy Azure SQL from the same network boundary.

### TAB strengths

- Keeps application data within the existing TAB network boundary.
- May reuse existing database operations, backup tooling and support skills.
- Can simplify access to on-premises systems that the application must read.

### TAB risks

- Power Apps is cloud-based, so cloud-to-on-premises connectivity must be
  explicitly designed and supported.
- Network outages can affect the app even when Power Apps itself is healthy.
- Database and API operations may have separate ownership and change windows.

## 4. Option B: PostgreSQL on an Azure VM

### Azure VM topology

```text
Power Apps cloud
      |
      | HTTPS + Entra token
      v
API host [Azure or TAB network]
      |
      | private endpoint/VNet route; no public PostgreSQL exposure
      v
PostgreSQL on Azure VM
      |
      +--> controlled route to TAB network if legacy references are required
```

### Azure VM required decisions

- Azure subscription, resource group, region and environment separation.
- VNet/subnet, NSGs, private DNS and administrator access path.
- VM size, managed disks, encryption, patching and maintenance ownership.
- PostgreSQL installation/version, backup target, retention and restore tests.
- High availability and disaster-recovery objective.
- Whether Azure Bastion, Just-In-Time access or another privileged access path
  is required.
- VPN or ExpressRoute connectivity to the TAB network for legacy references.
- Azure monitoring, alerting and ownership of the VM operating system.

### Azure VM strengths

- Convenient private proximity if the API is also hosted in Azure.
- Azure networking, identity, monitoring and backup services can be integrated.
- Easier future expansion if the application becomes Azure-hosted.

### Azure VM risks

- A VM creates an operating-system and PostgreSQL patching responsibility.
- Poor network configuration could accidentally expose PostgreSQL publicly.
- Azure cost and support ownership must include the VM, disks, backup and
  cross-network connectivity, not only the database software.

## 5. Initial recommendation

Keep both options open during logical design. Select the TAB-network option if
data residency, existing operations and local-system access dominate. Select
the Azure VM option if the API will be Azure-hosted and the organization can
own secure VM operations, private networking and backup/restore.

In either case, do not expose PostgreSQL directly to Power Apps. The API is the
security and domain boundary. A later managed PostgreSQL service can replace
the VM without changing the Power Apps contract if the application uses the
same PostgreSQL schema and API interfaces.

## 6. Placeholder configuration contract

These values are intentionally placeholders and must not be treated as
credentials or deployment instructions:

| Setting | TAB network placeholder | Azure VM placeholder |
| --- | --- | --- |
| Hostname | `<TAB-POSTGRES-HOST>` | `<AZURE-POSTGRES-VM-FQDN>` |
| Port | `<TAB-POSTGRES-PORT>` | `<AZURE-POSTGRES-PORT>` |
| Database | `<MILSTRIP-DB-NAME>` | `<MILSTRIP-DB-NAME>` |
| Schema | `milstrip_app` | `milstrip_app` |
| TLS mode | `<TAB-TLS-POLICY>` | `<AZURE-TLS-POLICY>` |
| Secret source | `<TAB-SECRET-SOURCE>` | `<AZURE-KEY-VAULT-OR-SECRET-SOURCE>` |
| API route | `<APPROVED-TAB-API-ROUTE>` | `<APPROVED-AZURE-API-ROUTE>` |
| Environment | `DEV / TEST / PROD` | `DEV / TEST / PROD` |

Actual hostnames, usernames, passwords, certificates and connection strings
must be supplied through the approved deployment/configuration process, never
committed to this repository.

## 7. Design gates

Before implementation:

1. Select the hosting option or approve a temporary DEV target.
2. Confirm API hosting location and private network path.
3. Define PostgreSQL ownership, patching, backup, restore and monitoring.
4. Approve the logical schema and retention policy.
5. Confirm Entra/AD FS SSO, Power Apps licensing and custom connector routing.
6. Complete a connectivity proof from API to PostgreSQL without exposing the
   database publicly.
7. Run a restore test and security review before production data is used.

**Current decision:** design both options; no infrastructure provisioning or
database creation is authorized by this document.
