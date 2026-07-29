## 1. Crawl and routing boundary

- [x] 1.1 Restrict SPA fallback to the currently supported browser routes.
- [x] 1.2 Return a real HTTP 404 with a usable noindex page for unknown paths.
- [x] 1.3 Redirect the `www` host to the apex host without changing the request path.

## 2. Search entry resources

- [x] 2.1 Publish a plain-text `robots.txt` with the canonical sitemap URL.
- [x] 2.2 Publish a valid XML sitemap containing only the public homepage.
- [x] 2.3 Add the absolute homepage canonical URL.

## 3. Crawlable homepage

- [x] 3.1 Include the existing H1, product summary, workflow, pricing model, privacy summary, and ordinary links in initial HTML.
- [x] 3.2 Add truthful Organization, WebSite, and SoftwareApplication JSON-LD.
- [x] 3.3 Preserve the existing React prototype and business behavior after startup.

## 4. Verification

- [x] 4.1 Add and run deterministic SEO P0 regression checks.
- [x] 4.2 Run focused Web tests and the production Web build.
- [x] 4.3 Validate the Nginx configuration.
- [x] 4.4 Run strict OpenSpec validation.
