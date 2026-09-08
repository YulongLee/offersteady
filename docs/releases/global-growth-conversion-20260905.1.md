# Global public growth and conversion release 2026-09-05.1

## Release

- Public host: `https://offersteady.com`
- Web version: `global-growth-conversion-20260905.1`
- Server release: `/opt/offersteady-global/releases/20260905-global-growth-conversion-1`
- New Web image: `sha256:8955898b18aa4d9d5e9bc051da59d53f0ab40c84dbaeb97dccfebf609bcc76f3`
- Baseline Web version: `global-seo-geo-20260905.1`
- Baseline Web image: `sha256:367366229766f09094628ba1184fd0f09495c82f352a48e90fbf5579f394898e`

## Shipped changes

- Trailing-slash public redirects preserve UTM and all other query parameters.
- `/download` exposes a server-readable Start Free link to `/login` and explains where verified Companion releases appear; no unapproved installer URL was published.
- Weak public titles and descriptions were improved while preserving unique self-canonicals and the disabled-payment boundary.
- Feature, guide, interview-question, and Download pages now include deeper verified workflow, limitation, troubleshooting, and responsible-use content.
- The homepage value proposition and supporting text use shorter, more direct English.
- The approved 1200 by 630 social image was reduced from 772,542 bytes to 294,122 bytes without changing its public URL or visual message.
- Release gates now cover metadata ranges, minimum useful growth-page content, Download actions, installer isolation, UTM redirects, social-image dimensions/size/hash, payment isolation, and existing route behavior.

## Verification

- Global component tests: 46 passed.
- Global typecheck, copy generation/audit, static generation, production build, merchant-review verifier, and deployment-asset verifier passed.
- Local Nginx container smoke passed for query-preserving redirects, Download action, login `noindex`, unknown-path 404, and public HTML.
- Chinese Web typecheck, tests, and production build passed; no Chinese Web source or production service was changed.
- Strict OpenSpec validation passed for `optimize-global-public-growth-conversion`.
- Overseas candidate image passed loopback checks before cutover.
- Production raw HTTP checks returned 200 for all 16 sitemap routes with route-specific title, description, canonical, H1, and body.
- Production `/features/?utm_source=review&utm_campaign=launch` redirects to `/features?utm_source=review&utm_campaign=launch`.
- Production `/download` contains the Start Free link and verified-release explanation.
- Production `/login` remains `noindex, nofollow`; an unknown path returns 404; `/healthz` remains healthy.
- Production social image returns `image/png`, `Content-Length: 294122`, and the expected cache policy.
- No recent Backend error was present after cutover.

## Service isolation

The active-interview query returned zero before candidate build and again immediately before cutover. Only `offersteady-global-web-1` was recreated. Backend, Admin, analytics, PostgreSQL, and Redis retained their existing containers and start times. The domestic deployment was not contacted or changed.

## Rollback

- Rollback tag: `offersteady-global-web:rollback-before-growth-conversion-20260905`
- Runtime backup: `/opt/offersteady-global/rollback/20260905-global-growth-conversion-1/`
- The backup contains the preceding Web root, inner Nginx configuration, baseline marker, and previous image identifier.
- Rollback recreates only the Global Web service. Do not restart Backend or remove PostgreSQL/Redis volumes.

## Deferred owner-controlled work

CDN and target-region field performance, Search Console, Bing Webmaster Tools, analytics/consent, product screenshots, customer proof, named reviewers, official social profiles, a domain-matching support address, and signed Global installers require account access, approved assets, or separate product decisions. No placeholder claims or identities were added in this release.
