# Global Admin hostname activation 20260904

## Deployment

- Public entry: `https://admin.offersteady.com`
- DNS target: `47.84.65.103`
- Upstream: `127.0.0.1:18881`
- TLS: Let's Encrypt certificate for `admin.offersteady.com`, with automatic renewal enabled
- Global Admin API: enabled with `https://admin.offersteady.com` as its allowed browser origin
- Scope: Global Nginx and Global Backend configuration only; Global Web, Admin image, PostgreSQL, Redis, and Chinese production were not restarted

## Acceptance

- DNS resolves to the Global host.
- HTTP redirects to HTTPS.
- HTTPS returns HTTP 200 with a matching certificate.
- An unauthenticated Admin session request returns HTTP 401, proving the route is present and protected.
- The public response includes no-index, CSP, anti-framing, MIME-sniffing, referrer, permissions, and HSTS protections.
- Global and Chinese production health endpoints returned HTTP 200 after activation.
- No Global administrator authorization existed at activation time. The first super administrator must be explicitly bootstrapped against an already registered Global phone login; no domestic identity is copied automatically.

## Rollback

- Nginx pre-hardening backup: `/etc/nginx/sites-available/admin.offersteady.com.certbot-20260904`
- Global private environment backup: `/opt/offersteady-global/releases/20260904-global-remove-user-manual-1/.env.global.production.before-admin-host-20260904`

Rollback must preserve the Global database and Redis volumes and must not modify Chinese production.
