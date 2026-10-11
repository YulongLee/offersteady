## 1. Content and static assets

- [x] 1.1 Create a single approved resource manifest for the directory and five report slugs, titles, summaries, categories, and review date.
- [x] 1.2 Convert the five reviewed Markdown reports into static HTML pages under `apps/web/public/resources/<slug>/index.html` using the existing public content layout and CSS.
- [x] 1.3 Create `apps/web/public/resources/index.html` with the resource directory, category labels, summaries, and links to all five report pages.
- [x] 1.4 Verify generated HTML contains no secrets, user data, business API calls, login-only content, or unapproved claims.

## 2. Public navigation and delivery

- [x] 2.1 Add “技术报告与资源中心” to the existing homepage “查看更多资源” area and the static homepage fallback without changing existing destinations.
- [x] 2.2 Add explicit Nginx routes for `/resources`, `/resources/`, and the five approved report URLs; unknown resource paths must remain 404.
- [x] 2.3 Add the six resource URLs to the public sitemap with the review date.

## 3. Verification

- [x] 3.1 Add static content tests for unique H1/title/description/canonical, JSON-LD, article links, and the six sitemap entries.
- [ ] 3.2 Run the resource tests, Web typecheck, existing SEO P0 checks, and production Web build.
- [ ] 3.3 Start the local Web preview and inspect `/resources/` plus at least one article on desktop and mobile viewport sizes.
- [x] 3.4 Update this task list with the actual verification results; do not deploy to CN production in this change.

## Verification notes (2026-10-11)

- Passed: `openspec validate add-cn-resource-center --strict`.
- Passed: `npm test -w @offersteady/web -- core-search-content.test.ts pricing-static.test.ts resource-center-static.test.ts` (36 tests), `npm run typecheck -w @offersteady/web`, `node apps/web/scripts/verify-indexing-build.mjs`.
- Passed: production Web build with `VITE_APP_ENV=production VITE_API_BASE_URL=/ VITE_PUBLIC_APP_VERSION=cn-resource-center-20261011.local npm run build -w @offersteady/web`.
- The existing `test:seo-p0` and `test:seo-build` suites remain blocked by unrelated pre-existing repository contracts (missing `$redirect_public_www` assertion and existing total-JS budget overage); no production deployment was performed.
- Local preview is running at `http://127.0.0.1:4173/`; resource directory and an article returned 200. Vite preview falls back to the SPA for unknown paths, while the added Nginx `try_files` routes keep unknown `/resources/*` paths at 404 in the production delivery layer.
