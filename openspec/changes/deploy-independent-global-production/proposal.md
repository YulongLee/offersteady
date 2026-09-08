## Why

The completed Global English application now has a dedicated overseas server and the `offersteady.com` domain. It must be deployed without sharing runtime state, credentials, data stores, release artifacts, or operational actions with the existing Chinese production system.

## What Changes

- Add an independent Global production deployment profile for `offersteady.com` on `47.84.65.103`.
- Deploy the English Web, shared Backend code, Chinese operator console, PostgreSQL, Redis, and reverse proxy as Global-only services and data stores.
- Use same-origin `/api` routing and HTTPS while keeping international commerce disabled until its provider and legal terms are approved.
- Create independent secrets, backups, logs, health checks, deployment markers, and rollback artifacts.
- Preserve any unrelated workloads already running on the overseas host and make no changes to the Chinese server or `mianshiwen.cn`.

## Capabilities

### New Capabilities

- `independent-global-production`: Covers isolated Global hosting, HTTPS routing, data and secret separation, safe rollout, verification, and rollback.

### Modified Capabilities

None.

## Impact

- Adds Global-specific infrastructure and deployment assets under `infra/`, `scripts/`, and deployment documentation.
- Creates new services and data only on `47.84.65.103`; existing Nginx workloads on that host must remain available.
- Does not modify the Chinese Web application, Chinese production host, domestic domain, or domestic databases.
- Processes Global account, interview, transcript, screenshot, and material data in the new isolated environment; raw audio remains non-persistent by default.
