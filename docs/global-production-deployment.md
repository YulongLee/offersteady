# Global production deployment

## Scope

`offersteady.com` is deployed on `47.84.65.103` as the independent `offersteady-global` Compose project. It uses its own PostgreSQL and Redis volumes, application secrets, loopback ports, build artifacts, release marker, and rollback history. It does not connect to or deploy against the Chinese production host.

The public Global Web, shared Backend, and authenticated Global operator console are exposed through host Nginx. The operator console uses the isolated `admin.offersteady.com` hostname, carries no public customer navigation entry, and continues to require application authentication and authorization.

## Port and routing boundary

- Public `80/443`: existing host Nginx
- Global Web: `127.0.0.1:18880`
- Global Backend diagnostic endpoint: `127.0.0.1:18000`
- Global Admin upstream: `127.0.0.1:18881`
- Global Admin public entry: `https://admin.offersteady.com` (application authentication remains mandatory)
- Global PostgreSQL and Redis: internal Docker network only

Browser API calls use `https://offersteady.com/api/...`. Realtime SSE and API responses have proxy buffering disabled in both Nginx layers.

## Private environment

The server file `.env.global.production` must be mode `0600` and must never be committed. It contains fresh Global first-party secrets and database credentials. Only explicitly approved external-provider variables may be migrated from another environment, without logging their values. Domestic database, Redis, public URL, callback URL, payment, and release variables must never be copied.

The Backend production selector is `OFFERSTEADY_ENVIRONMENT=production`; `OFFERSTEADY_ENV` is legacy deployment metadata and does not replace it.

The Global operator console is built with `VITE_PRODUCT_EDITION=global` and uses the Global email verification-code endpoints. Administrator access is still decided by the isolated server-side `admin_authorizations` table; verifying an unapproved email never grants operator access. The Chinese Admin continues to use its phone/SMS login build.

Object storage must use `OFFERSTEADY_OSS_KEY_PREFIX=global` and `OFFERSTEADY_OSS_ENVIRONMENT_LABEL=production`. Before Creem testing, commerce remains disabled with `GLOBAL_COMMERCE_PROVIDER=none`, `GLOBAL_COMMERCE_ENABLED=false`, and `OFFERSTEADY_GLOBAL_COMMERCE_ENABLED=false`. For an approved sandbox exercise, use `GLOBAL_COMMERCE_PROVIDER=creem`, `GLOBAL_COMMERCE_ENABLED=true`, `OFFERSTEADY_GLOBAL_COMMERCE_ENABLED=true`, and `OFFERSTEADY_GLOBAL_COMMERCE_PROVIDER_MODE=test`; the database Test activation flag still fails closed until the administrator explicitly enables it. Do not place a Creem API key or webhook secret in any `VITE_` variable.

Creem API Key and Webhook Secret can be replaced in the authenticated Global Admin. They are encrypted with `OFFERSTEADY_ADMIN_ENCRYPTION_KEY`, stored separately for Test and Live, and never returned to the browser. Environment credentials remain a backward-compatible fallback. The Admin retrieves provider products through Creem and maps only the four paid OfferSteady plans; Free does not require a Creem product.

## Deployment and verification

From the versioned server release directory:

```bash
chmod +x scripts/deploy-global-production.sh scripts/test-global-deployment-assets.sh
scripts/test-global-deployment-assets.sh
scripts/deploy-global-production.sh
```

After the loopback checks pass, install `infra/nginx/offersteady.com.conf` as a new host virtual host, run `nginx -t`, reload Nginx, and issue a certificate for both `offersteady.com` and `www.offersteady.com`. Verify:

- both hostnames have a valid certificate and canonical Global content;
- `/healthz`, `/api/v1/web/state`, and the production build manifest succeed;
- English login, preparation, live interview, screenshot, review, and help routes render;
- `/offersteady-global-build.json` matches the intended `false:none` or `true:creem` release flags and contains no loopback or domestic endpoint;
- PostgreSQL and Redis have no public host binding;
- existing overseas domains and the domestic production health endpoint are unchanged.

Verification logs must not include credentials, transcript text, screenshots, resumes, job descriptions, or source documents.

## Rollback

Keep the previous versioned release directory and Nginx file backup. To roll back, run the same Compose project against the preceding release and environment file, then validate and reload the preceding Nginx configuration. Never use `docker compose down --volumes` and never delete the named PostgreSQL or Redis volumes during application rollback.

## Commercial-launch blockers

Technical availability is not commercial readiness. Before public launch, separately approve and test:

- international authentication or OTP for the US, UK, Australia, and Canada;
- Global-specific AI, storage, parsing, email, and observability accounts and data residency;
- payment provider, legal entity, currencies, tax, refunds, privacy terms, and required disclosures;
- protected operator-console hostname and access policy;
- signed and notarized Global desktop installers and their independent update channel.

Creem Test and Live data are isolated. Test acceptance uses the Test API key, Test webhook, and Test products. After merchant approval, recreate or verify the four products in Live, configure the Live credentials and webhook in Global Admin, switch `OFFERSTEADY_GLOBAL_COMMERCE_PROVIDER_MODE=live`, redeploy, validate all Live mappings, and explicitly enable Live. Never copy Test Product IDs into Live.
## Global email authentication activation gate

The Global customer Web uses email verification for registration and sign-in. Do not publish that Web build until the isolated Global Backend has a verified transactional sender and passes the email smoke tests documented in `docs/environment-variables.md`.

Required production settings are `OFFERSTEADY_AUTH_EMAIL_ENABLED=true`, `OFFERSTEADY_AUTH_EMAIL_PROVIDER_MODE=smtp`, an independent code pepper, SMTP host/port/credentials, and a verified from address/name. Missing values fail closed. Keep the previous Global Web and Backend image tags available for rollback; do not copy domestic users or SMS secrets into the Global database.
