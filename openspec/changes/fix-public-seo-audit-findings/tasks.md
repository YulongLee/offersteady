## 1. Route-specific public HTML

- [x] 1.1 Add a dedicated Vite guide entry with guide-specific title, description, self-canonical, structured data, H1, summary, and public navigation.
- [x] 1.2 Make the homepage entry title more descriptive and expose an ordinary `/guide` link while preserving visible product behavior.
- [x] 1.3 Configure the Web production build to emit distinct homepage and guide HTML documents.
- [x] 1.4 Prevent React startup from overwriting route-specific guide and legal-page titles.

## 2. Ingress and caching

- [x] 2.1 Serve `/guide` from the dedicated guide document while preserving the existing React route.
- [x] 2.2 Apply revalidation-friendly caching to indexable public HTML and retain `no-store` for private/noindex HTML.
- [x] 2.3 Update content-security hashes for the approved route-specific JSON-LD without weakening existing headers.

## 3. Release protection

- [x] 3.1 Extend SEO regression checks for sitemap-to-entry mapping, distinct metadata, self-canonical URLs, crawlable public links, and split cache policies.
- [x] 3.2 Add production-build assertions for distinct `dist/index.html` and `dist/guide.html` outputs.

## 4. Verification

- [x] 4.1 Run focused Web tests, SEO regression checks, type checking, and the production build.
- [x] 4.2 Validate Nginx syntax or its deterministic configuration contract and smoke-test both public routes.
- [x] 4.3 Run strict OpenSpec validation and update the SEO audit artifacts with the implemented status.
