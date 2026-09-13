## 1. Page targeting

- [x] 1.1 Update homepage initial HTML and metadata for broad keyword ownership and descriptive feature links.
- [x] 1.2 Update realtime SEO page title, H1, opening answer, process copy, and links for realtime keywords.
- [x] 1.3 Update technical assistant SEO page title, H1, opening answer, and technical topic cluster links.
- [x] 1.4 Update pricing SEO page title, H1, opening answer, and dynamic-price boundary wording.

## 2. GEO and cannibalization

- [x] 2.1 Adjust feature hub and supporting page anchors so broad terms remain secondary to the homepage.
- [x] 2.2 Update `llms.txt`, `llms-full.txt`, and `public-facts.json` with direct factual answers and official URLs.
- [x] 2.3 Add or update regression checks for unique titles, H1s, canonicals, target phrases, and prohibited claims.

## 3. Verification

- [x] 3.1 Run SEO P0/build verification and Web typecheck/build/tests; record unrelated baseline failures without widening scope.
- [x] 3.2 Inspect generated initial HTML for the four owner pages and confirm sitemap/canonical consistency.
- [x] 3.3 Run `openspec validate optimize-cn-keyword-targeting --strict`.
- [x] 3.4 Record the existing verified ten-keyword baseline; defer re-query until after deployment/indexing to avoid consuming ranking quota.
