# Global Creem merchant-review crawler fix 20260904.2

- Host: `47.84.65.103`
- Public domain: `https://offersteady.com`
- Release: `global-creem-review-20260904.2`
- Release path: `/opt/offersteady-global/releases/20260904-global-creem-review-2`
- Scope: Global Web only

## Correction

- Removed the stale payment-approval sentence from the home-page initial HTML.
- Made `$19.99/week` and `$39.99/month` contiguous literal text in the raw Pricing HTML.
- Added explicit Nginx locations for Pricing, Terms, Privacy, Refund Policy, Contact, About, and Security. These URLs return their static entry or HTTP 404 and can no longer fall through to the SPA home shell.
- Added explicit index/follow and revalidation response headers for the seven review routes.

## Production evidence

- The production manifest reports `global-creem-review-20260904.2` with commerce disabled.
- Direct no-JavaScript `curl` requests returned HTTP 200 and unique title, description, canonical, H1, and body for all seven routes.
- Raw Pricing HTML contains the exact strings `$19.99/week` and `$39.99/month`.
- Terms, Contact, and About raw HTML contain the approved operator identity.
- Refund Policy has its own static H1 and body.
- Curl, Googlebot, Bingbot, ChatGPT-User, and Creem-review user agents returned the same Pricing body hash.
- Cloudflare, Google, Quad9, AliDNS, and 114DNS resolved `offersteady.com` to the same production address; both authoritative DNS servers returned that address.
- Robots and sitemap checks passed. The independent SEO parser read the expected Pricing metadata and headings.
- Only the Global Web container was recreated; the other Global services were not restarted.

## Rollback

The immediately preceding Web image is retained as `offersteady-global-web:rollback-before-creem-review-20260904-2`. Rollback must recreate only the Global Web service and must not restart Backend or remove PostgreSQL/Redis volumes.
