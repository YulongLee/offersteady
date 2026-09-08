# Global Creem merchant-review release 20260904.1

- Host: `47.84.65.103`
- Public domain: `https://offersteady.com`
- Release: `global-creem-review-20260904.1`
- Release path: `/opt/offersteady-global/releases/20260904-global-creem-review-1`
- Scope: Global Web only

## Deployment result

- Deployed route-specific initial HTML for Pricing, Terms, Privacy, Refund Policy, Contact, About, and Security.
- Published the approved pre-payment pricing and kept Global commerce disabled.
- Published Global sitemap, robots, canonical, operator, support, refund, and responsible-use disclosures.
- Rebuilt and recreated only `offersteady-global-web-1`. Backend, Admin, Analytics, PostgreSQL, and Redis were not restarted.
- Both `offersteady.com` and `www.offersteady.com` returned HTTP 200 with the new Pricing title.
- Public health, core Web state API, build manifest, seven direct page responses, sitemap, robots, and Nginx syntax passed after deployment.

## Rollback

The preceding Web image is retained as `offersteady-global-web:rollback-before-creem-review-20260904`, with image ID recorded by the deployment log. Recreate only the Global Web service from that image if rollback is required. Do not restart Backend or remove PostgreSQL/Redis volumes.
