## Context

The Global product is a React/Vite application served by an inner Nginx container behind host Nginx. Seven merchant-review routes have dedicated static HTML, but the remaining public links fall through to `index.html`; the same fallback also converts unknown paths and missing GEO files into HTTP 200 homepage responses. The international application, Backend, database, realtime transports, and domestic product must remain unchanged.

The international user manual was intentionally removed. `/guide` and “User guide” are therefore not part of the new public search surface even though stale homepage output still links to that path.

## Goals / Non-Goals

**Goals:**

- Make every approved public search route useful and identifiable without JavaScript.
- Make status codes, index controls, canonical host, sitemap, GEO files, and metadata internally consistent.
- Add enough truthful English product context for search discovery and AI citation without unsupported claims.
- Improve public static delivery and security while isolating realtime and authenticated traffic.
- Make production fallback regressions fail automated verification.

**Non-Goals:**

- No user manual for the Global product.
- No new authenticated features, APIs, database tables, analytics, cookies, payment activation, or Creem calls.
- No changes to interview, Companion, ASR, RAG, screenshot, prompt, billing-entitlement, or email-login behavior.
- No fabricated reviews, ratings, user counts, success rates, performance claims, official platform integrations, or deceptive-use marketing.
- No large programmatic page set or country-keyword permutations.

## Decisions

### Generate all indexable public HTML and discovery artifacts from one catalogue

Extend the existing build-time public-page catalogue/generator into a single Global public-search registry. The registry will own route, intent, title, description, H1, sections, update date, and schema inputs. The generator will emit the static HTML entries, sitemap, `llms.txt`, `llms-full.txt`, and `public-facts.json` from that registry.

This avoids drift between handwritten Nginx regexes, HTML, sitemap, and GEO resources. A runtime SSR framework was rejected because the product already has a low-risk static entry pattern and the change must not add backend/runtime dependencies.

### Publish a small, verified route set

The first indexable growth surface will contain the homepage, the existing merchant-review pages, `/features`, four existing feature routes, `/guides`, `/interview-questions`, and `/download`. Hubs will explain the available product and preparation categories; they will not advertise unpublished child articles. The stale `/guide` link will be removed and `/guide` will not enter the sitemap.

This is preferred to generating many thin pages. Additional detailed guides or topic pages require verified content and a later reviewed change.

### Separate public routing from application routing at ingress

Exact static mappings will be evaluated before the SPA route group. Unknown top-level paths will return a real 404. Application routes such as `/login`, `/app`, `/error`, and legacy referral paths remain functional but receive a server-visible `X-Robots-Tag: noindex, nofollow`. API, SSE, WebSocket, health, and referral proxy blocks remain unchanged.

This is preferred to relying on React metadata because crawlers may inspect the initial response and HTTP status before rendering JavaScript.

### Canonicalise at the outer host boundary

The checked-in host configuration will use separate apex and `www` server blocks so `www` redirects permanently to the same apex path and query. Production changes will preserve Certbot-managed certificate paths and be applied only after `nginx -t` succeeds.

### Keep public caching isolated

Fingerprint assets remain immutable. Indexable public HTML and discovery files use short revalidation caching; authenticated SPA documents remain `no-store`. Public CDN adoption is deferred until regional measurements and DNS ownership are available, because changing proxy topology is materially riskier than this static release.

### Add truthful, portable schema only

The homepage will expose `Organization`, `WebSite`, and `SoftwareApplication`; Pricing will expose visible plan offers without claiming checkout availability; public subpages will expose `WebPage` and `BreadcrumbList`. No review or aggregate-rating schema will be generated.

## Risks / Trade-offs

- [Static copy can drift from the hydrated React view] → Generate initial HTML and route metadata from one catalogue and assert matching titles, canonicals, H1s, links, and facts after build.
- [A strict 404 can break a legitimate SPA route] → Maintain an explicit application-route allowlist, exercise every existing Global route in tests, and keep rollback to the prior Web image/config.
- [Security headers can break scripts or realtime connections] → Preserve current CSP sources, add only header values already compatible with the build, and smoke-test login and interview entry.
- [Outer Nginx canonical redirect can affect WebSocket/API clients using `www`] → Preserve path/query and standardise public/API clients on the apex host before enabling the redirect.
- [More copy can reduce conversion clarity] → Keep the approved visual structure, add concise sections below the primary CTA, and avoid a redesign.
- [GEO files may be treated as authoritative despite becoming stale] → Generate them from the same verified catalogue as visible HTML and fail builds on contradictions.

## Migration Plan

1. Record the deployed Global release marker, container state, public route responses, and current host/inner Nginx configuration without exposing secrets.
2. Build and test the Global Web locally, including exact route, unknown-path, noindex, sitemap, schema, GEO MIME/body, social metadata, and prohibited-copy checks.
3. Create a versioned server release and build only the Global Web image; do not rebuild or restart Backend, PostgreSQL, Redis, analytics, admin, or domestic services.
4. Validate the new Web on loopback before switching the public container/config.
5. Back up host Nginx, apply the reviewed canonical-host block, run `nginx -t`, and reload only Nginx.
6. Verify every public URL with raw `curl` and an HTML parser, then smoke-test login and the Global Backend health endpoint.
7. Roll back the Global Web image and Nginx backup together if any existing application route, health check, API, or index contract regresses.

## Open Questions

- Search Console, Bing Webmaster Tools, analytics, regional CrUX, and backlink data remain unavailable; deployment will not claim ranking or field-performance improvement.
- A domain-matching support alias and official social profiles require owner-provided accounts and are not added in this change.
- CDN activation remains a separate infrastructure decision after regional measurements.

