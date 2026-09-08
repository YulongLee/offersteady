## 1. Deployment assets

- [x] 1.1 Add a Global Web image, isolated Compose profile, host Nginx template, and secret-safe deployment script.
- [x] 1.2 Document the deployment, provider boundary, rollback procedure, and commercial-readiness blockers.
- [x] 1.3 Add static validation for domain isolation, loopback-only service exposure, disabled commerce, and non-destructive rollback.

## 2. Local verification

- [x] 2.1 Strictly validate the OpenSpec change.
- [x] 2.2 Build and test the Global Web, shared Backend, Chinese Admin, and deployment configuration.
- [x] 2.3 Verify no deployment asset contains domestic production endpoints or committed secrets.

## 3. Overseas rollout

- [x] 3.1 Record read-only overseas host, DNS, port, workload, disk, memory, and Nginx baselines.
- [x] 3.2 Install missing container prerequisites without replacing existing host services.
- [x] 3.3 Create independent Global secrets and securely migrate only the approved external-provider allowlist.
- [x] 3.4 Upload and start the Global-only stack without exposing PostgreSQL or Redis.
- [x] 3.5 Add the domain-specific Nginx route and obtain valid TLS for the root and `www` hostnames.

## 4. Production verification and handoff

- [x] 4.1 Verify HTTPS, health, same-origin API, production manifest, English routes, commerce-disabled behavior, and realtime proxy settings.
- [x] 4.2 Verify all pre-existing overseas services and the domestic production endpoint remain healthy and unchanged.
- [x] 4.3 Record the deployed revision, rollback target, operational URLs, and unresolved commercial-launch blockers.
