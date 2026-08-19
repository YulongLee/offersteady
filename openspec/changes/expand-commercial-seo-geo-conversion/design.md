## Context

The current production Web image serves the React product plus eight explicit server-delivered public documents through Nginx. Public discovery already has canonical metadata, structured data, sitemap coverage, real 404 responses, GEO discovery files, and deterministic release checks. The remaining gap is commercial breadth and authority: decision-stage visitors cannot reach dedicated public pricing, download, security, identity, or contact pages, while troubleshooting and preparation content covers only two broad intents.

The repository contains unrelated in-progress backend, SMS, material, and deployment edits. This change must avoid those files and remain independently reviewable and deployable as a Web-only release.

## Goals / Non-Goals

**Goals:**

- Add five static commercial decision pages and four distinct, high-intent guides.
- Keep every new page useful without JavaScript, self-canonical, internally linked, and covered by release verification.
- Explain dynamic pricing and download availability truthfully without copying mutable backend catalog or release state into static HTML.
- Improve guide ownership, maintenance dates, sources, and extractable answer passages for search and answer engines.
- Preserve the existing product boundary and avoid unverified legal, customer, ranking, outcome, integration, and performance claims.

**Non-Goals:**

- No analytics provider, tracking cookie, Search Console mutation, sitemap submission, backlink campaign, CMS, SSR framework, or programmatic page generator.
- No exact static price catalog or static desktop download URL that can drift from backend-managed state.
- No legal operator name, social profile, author identity, customer story, rating, review, or benchmark without verification.
- No changes to authenticated routes or any backend, database, interview, realtime, screenshot, material, billing, payment, membership, admin, or desktop behavior.

## Decisions

### Extend the existing static public document pattern

New pages will live under the existing public SEO document directory, share the current lightweight stylesheet, and use explicit Nginx route mappings. This avoids importing the authenticated SPA bundle or introducing a CMS/SSR runtime. A static page may link users into the existing login and guide routes but will not call private APIs.

### Separate stable commercial explanations from mutable catalog state

The pricing page will explain points, memberships, charging boundaries, payment confirmation, and where authoritative current prices appear. The download page will explain supported platforms, permissions, architecture selection, and the authoritative in-product download center. Exact catalog prices, release versions, checksums, and downloadable artifact URLs remain backend-controlled.

This is preferred over duplicating backend state into build-time HTML because stale commercial or binary information is worse than a clear authoritative handoff.

### Publish only a curated first guide cluster

The first expansion covers macOS permissions, Feishu audio setup, Tencent Meeting audio setup, and STAR answer structure. Each addresses a distinct observed workflow or common preparation intent. Platform names are used only to describe user setup scenarios and pages will explicitly avoid claiming official partnership or direct integration.

This is preferred over mass-generated role/location pages because the current site has no search-demand or conversion dataset to justify broad scale.

### Use organization-level editorial ownership until an individual author is verified

Guide pages will visibly identify “面试稳产品与支持团队” as the reviewing organization, show publication and modified dates, and cite maintained product/legal pages or official operating-system/platform documentation where appropriate. JSON-LD will use Article with Organization as author/publisher and BreadcrumbList. No Person schema will be added without a verified named author.

### Make search-oriented AI access explicit without changing crawler policy

robots.txt will explicitly allow GPTBot, OAI-SearchBot, ChatGPT-User, ClaudeBot, and PerplexityBot while retaining the existing wildcard allow and sitemap. Training-crawler policy remains unchanged rather than being guessed. GEO source files will link to the new canonical pages and distinguish stable facts from dynamic product state.

## Risks / Trade-offs

- [Static commercial copy can drift] → Keep mutable prices, releases, payment channels, and support values delegated to existing authoritative product surfaces and validate that static copy names those boundaries.
- [Platform-specific guides could imply affiliation] → Include a concise non-affiliation statement and describe only user-controlled settings.
- [More pages can dilute quality] → Limit this release to nine pages with unique intent, substantive copy, and bidirectional internal links.
- [Organization authorship provides less E-E-A-T than a named expert] → Use truthful team ownership now and leave Person schema for a later verified-author release.
- [Explicit AI crawler rules can become stale] → Keep them declarative and covered by release checks; do not change training permissions without a separate decision.

## Migration Plan

1. Add and validate the nine static documents, shared style extensions, sitemap entries, GEO references, and Nginx routes.
2. Add homepage/guide links and deterministic source/build tests without touching authenticated behavior.
3. Run OpenSpec strict validation, SEO/GEO scripts, Web tests, workspace typechecks, production build, and local route smoke checks.
4. Deploy the Web image only after explicit user direction; preserve backend, database, Redis, admin, and desktop containers.
5. Roll back the Web image and commit together if any public or existing product route regresses.

## Open Questions

- The registered legal operator remains unverified and will not be inferred from the SMS signature.
- Individual editorial authors and external brand profiles remain unverified.
- Search demand, rankings, impressions, AI citations, and organic conversion remain unknown until first-party search and analytics data are connected.
