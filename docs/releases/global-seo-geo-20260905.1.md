# Global SEO/GEO public-search release 20260905.1

## Deployment

- Host: `47.84.65.103`
- Public URL: `https://offersteady.com`
- Release: `global-seo-geo-20260905.1`
- Release path: `/opt/offersteady-global/releases/20260905-global-seo-geo-1`
- Compose project: `offersteady-global`
- Scope: Global public Web and host Nginx only
- Web image: `sha256:367366229766f09094628ba1184fd0f09495c82f352a48e90fbf5579f394898e`
- Global commerce: disabled; browser provider remains `none`

## Delivered

- Added server-readable Features, four capability pages, Guides, Interview Questions, and Download pages.
- Generated all 15 public subpages, sitemap, `llms.txt`, `llms-full.txt`, and `public-facts.json` from one verified public catalogue.
- Added route-specific metadata, social preview metadata, and truthful Organization, WebSite, SoftwareApplication, Offer, WebPage, and BreadcrumbList JSON-LD.
- Expanded the homepage source content and public navigation without changing the authenticated interview application.
- Removed the stale public User Manual route and made unknown paths return a real HTTP 404.
- Added server-visible noindex controls for login/application routes, a path-preserving `www` canonical redirect, and reviewed public security/cache headers.

## Verification

- Global product tests: 45 passed.
- Chinese Web regression tests: 349 passed.
- Global and Chinese production builds passed.
- Global copy audit, merchant-review/public-search audit, deployment-boundary checks, strict OpenSpec validation, and local Nginx HTTP smoke tests passed.
- All 16 production indexable URLs returned unique canonical/H1 content in raw HTTP responses.
- Pricing raw HTML contained `$19.99/week` and `$39.99/month`; paid actions remained `Coming Soon`.
- GEO files returned correct MIME types, sitemap contained 16 canonical URLs with 16 `lastmod` entries, login/application routes returned noindex, and unknown paths returned 404.
- Backend health remained `ok`. Backend, PostgreSQL, Redis, Admin, and Analytics container start times did not change.

## Rollback

- Previous source release: `/opt/offersteady-global/releases/20260904-global-creem-review-2`
- Previous host Nginx: `/opt/offersteady-global/rollback/20260905-global-seo-geo-1/offersteady-global.nginx`
- Previous built Web root and inner Nginx configuration: `/opt/offersteady-global/rollback/20260905-global-seo-geo-1/web-root` and `global-web.conf`

Rollback must replace only the Global Web runtime and host Nginx configuration. It must not restart Backend, PostgreSQL, Redis, Admin, Analytics, or any domestic service.
