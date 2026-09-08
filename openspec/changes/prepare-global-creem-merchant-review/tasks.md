## 1. Public Page Model and Browser Routes

- [x] 1.1 Add a shared Global public-page catalogue with approved pricing, operator, support, compliance, and metadata facts.
- [x] 1.2 Add browser-rendered Pricing, Refund Policy, Terms, Privacy, Contact, About, and Security routes and footer navigation.

## 2. Crawler-Readable Build Output

- [x] 2.1 Generate an independent initial HTML entry for every required public URL and include each entry in the Vite build.
- [x] 2.2 Update Global Nginx static routing so extensionless public URLs resolve to their own HTML entry before the SPA fallback.
- [x] 2.3 Add Global robots and sitemap files with matching canonical HTTPS URLs.

## 3. Regression and Review Verification

- [x] 3.1 Add tests for approved prices, disabled payment controls, operator/support consistency, footer links, and responsible-use copy.
- [x] 3.2 Build and serve the Global site locally, then verify direct HTTP metadata, H1, body, canonical, sitemap, and robots responses.
- [x] 3.3 Run Global application regression tests, OpenSpec strict validation, and confirm no core workflow or API files changed for this remediation.

## 4. Production Crawler Consistency

- [x] 4.1 Remove stale pre-launch pricing copy from the home-page initial HTML and expose contiguous paid price terms in raw Pricing HTML.
- [x] 4.2 Pin all seven review URLs to explicit Nginx static-page locations so none can fall through to the SPA home shell.
- [x] 4.3 Deploy only the Global Web service and verify raw production responses across DNS, crawler user agents, sitemap, robots, and canonical metadata.
