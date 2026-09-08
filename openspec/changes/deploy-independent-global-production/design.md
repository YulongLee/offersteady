## Context

The English Global application is implemented in the shared monorepo, while the Chinese production application must remain untouched. The new host (`47.84.65.103`) already runs unrelated native Nginx, PostgreSQL, and Node services. The root and `www` records for `offersteady.com` resolve to this host; no API subdomain is required because the Web application uses same-origin API routes.

The first deployment is a technical preview. International payment is intentionally disabled, and international authentication/provider/legal readiness is not yet established.

## Goals / Non-Goals

**Goals:**

- Deploy the Global Web and shared Backend on the overseas host with isolated state and secrets.
- Preserve existing overseas workloads and all Chinese production systems.
- Provide valid HTTPS, same-origin API routing, health checks, and rollback.
- Make deployment output and runtime logging safe for user and secret data.

**Non-Goals:**

- Enabling international payments, tax handling, refunds, or paid plans.
- Reusing the domestic database, Redis, sessions, orders, or user accounts.
- Migrating or modifying unrelated services already running on the overseas host.
- Claiming commercial readiness before international providers and policies are approved.

## Decisions

### Run a dedicated Compose project behind the existing host Nginx

Use the project name `offersteady-global` and bind Web, Backend, and Admin only to explicit loopback high ports. PostgreSQL and Redis stay on a private Docker network with no host port. The host Nginx remains the sole public listener on ports 80 and 443 and receives one new virtual host for the Global domain.

This avoids port conflicts with the host's native PostgreSQL and existing Node services. Installing the Docker runtime changes the host package set but does not replace or reconfigure current processes.

### Keep public traffic same-origin

The browser calls `/api` on `offersteady.com`. The Global Web container proxies API and realtime routes to the Global Backend container, including disabled buffering for SSE. The host Nginx proxies the domain to the loopback Global Web port and also disables response buffering for realtime paths.

This avoids a second DNS and certificate dependency and prevents accidentally targeting a domestic API origin.

### Separate first-party state and secrets

Generate new database, JWT, admin-session, encryption, visitor-HMAC, material-hash, redemption, and access-token secrets on the overseas host. Store the environment file outside Git with mode `0600`. The Global database, Redis data, and release marker use Global-only names.

External AI, SMS, parsing, and object-storage provider credentials may be copied through a non-logging allowlist as a temporary integration measure. They remain external account dependencies rather than shared application state. Object storage uses a Global-specific prefix and environment label. Domestic database URLs, Redis URLs, payment credentials, and public URLs are never copied.

### Disable commerce and limit operator exposure

Build the Global Web with `VITE_GLOBAL_COMMERCE_ENABLED=false` and leave checkout provider configuration empty. The Chinese Admin build is available only on a loopback port until a separate protected operator hostname and access policy are approved.

### Use safe, reversible host integration

Before changing Nginx, capture its enabled-site list, listening ports, process health, and a timestamped copy of the affected configuration. Validate with `nginx -t` before reload. Obtain a certificate only after the HTTP route is healthy. Application rollback reuses the prior release directory or images and never removes data volumes.

### Bootstrap schema without copying domestic business data

The historical SQL chain contains table definitions that evolved incrementally and cannot safely initialize a brand-new database as one flat batch. For the first Global preview, copy only the stable production schema definition and schema-migration metadata into a new empty Global database. Do not copy table data for users, authentication sessions, interviews, transcripts, materials, orders, payments, points, promotion, or analytics. Verify zero Global users and zero Global interviews after bootstrap, then retain a Global-only schema baseline for recovery.

## Risks / Trade-offs

- **Shared external provider accounts during preview** → Isolate keys from clients and Global first-party data, use a separate storage prefix, document this as a commercial-launch blocker, and replace with Global-specific accounts later.
- **Aliyun SMS may not support target-region phone numbers** → Treat authentication as preview-only until international OTP or another login method is selected and tested.
- **2 vCPU / 4 GiB host also runs other workloads** → Build serially, set restart policies, avoid exposing database/cache ports, and verify host memory and existing services before and after deployment.
- **Host Nginx is shared infrastructure** → Add only a domain-specific file, validate before reload, and retain the prior file for immediate rollback.
- **Certificate issuance can fail** → Keep an HTTP health endpoint working and do not claim completion until both approved hostnames validate over HTTPS.

## Migration Plan

1. Record the source revision, DNS results, existing host services, ports, memory, and Nginx configuration.
2. Install Docker only if absent and verify existing workloads remain healthy.
3. Upload a versioned source release and create the Global-only environment file without logging values.
4. Build and start the isolated Compose project serially; initialize only its new database from schema-only metadata and verify that no business rows were copied.
5. Add and validate the `offersteady.com` Nginx virtual host, then issue and verify TLS.
6. Verify health, build manifest, English pages, same-origin API, commerce-disabled behavior, port isolation, and existing host services.
7. On failure, restore the previous application release and Nginx file without deleting Global volumes.

## Open Questions

- Which international authentication/OTP provider will support the US, UK, Australia, and Canada launch regions?
- Which Global-specific AI, object-storage, document-parsing, email, and observability accounts will replace transitional provider credentials?
- Which payment provider, legal entity, currencies, tax model, refund policy, privacy terms, and data-residency policy will be approved?
- What protected hostname and access control should expose the Chinese operator console?
