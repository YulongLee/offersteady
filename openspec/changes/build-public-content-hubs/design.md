## Context

OfferSteady currently serves its public SEO pages as small static HTML documents behind explicit Nginx route mappings. This makes the content indexable without JavaScript and isolates public publishing from the authenticated React application. The current 17-page surface has commercial and guide pages, but no directory-level pages for product capabilities, editorial guides, or interview-question topics.

## Goals / Non-Goals

**Goals:**

- Add three fast, server-rendered hubs that make the public information architecture understandable to visitors and crawlers.
- Distinguish the product manual (`/guide`) from the editorial guide directory (`/guides`).
- Reuse verified product facts, existing canonical pages, shared styling, and deterministic release checks.
- Keep every linked child page real and useful at the time the hub ships.

**Non-Goals:**

- No authenticated UI, API, database, desktop, billing, interview, audio, or screenshot changes.
- No empty category children, programmatic article generation, user-generated content, fake reviews, or unverified performance claims.
- No renaming of existing public URLs or migration redirects.

## Decisions

1. **Continue using static public HTML and explicit Nginx mappings.** This matches the current deployment model and keeps the new pages independent of API availability. A React route implementation was rejected because it would require JavaScript and could expose the product shell's backend-loading state to crawlers.
2. **Use three distinct search intents.** `/features` explains what the product does; `/guides` helps users prepare and configure use; `/interview-questions` explains the planned topic taxonomy and links only to already published relevant resources. Combining them into one directory was rejected because it blurs conversion and informational intent.
3. **Use WebPage and BreadcrumbList structured data.** The hubs are directories, not authored articles, so Article markup would misrepresent them. FAQ markup remains excluded because visible FAQs do not require rich-result schema and search engines have narrowed FAQ eligibility.
4. **Use shared design primitives and hand-authored content.** This keeps visual consistency and quality control. The hubs will not introduce a CMS or templating dependency at this stage.
5. **Treat discovery artifacts and release checks as one atomic release.** A hub is not complete until its route, canonical, sitemap, GEO sources, navigation, and validation agree.

## Risks / Trade-offs

- **[Risk] Hub pages can become thin if child content is limited.** → Include useful orientation, selection guidance, boundaries, and existing-page summaries rather than only link grids.
- **[Risk] `/guide` and `/guides` may be confused.** → Label them consistently as “使用手册” and “面试指南” in titles, headings, navigation, and explanatory copy.
- **[Risk] Static links can drift as content grows.** → Validate internal links and canonical routes in deterministic source and build checks.
- **[Risk] New public routes could fall through to the SPA.** → Add exact-match Nginx locations and online response checks.

## Migration Plan

1. Add the three documents and discovery/navigation references.
2. Run source verification, unit tests, type checks, production build checks, and OpenSpec strict validation.
3. Publish the Web image only; leave backend, database, and desktop services unchanged.
4. Smoke-test all 20 public routes and key noindex/404 behavior online.
5. Roll back to the previous Web image/commit if any public-route or application-shell regression appears.

## Open Questions

None for this change. Child article priorities and comparison content are intentionally deferred to separate reviewed changes.
