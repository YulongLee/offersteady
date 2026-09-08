## ADDED Requirements

### Requirement: Global ingress MUST return meaningful status and index controls
The Global ingress MUST route approved public documents before the SPA fallback, return HTTP 404 for unknown public paths, and expose server-visible noindex controls for non-search application routes.

#### Scenario: Unknown URL is requested
- **WHEN** a request targets a path outside the approved public, application, API, health, and referral route sets
- **THEN** the server returns HTTP 404 and does not return the homepage document

#### Scenario: Login or authenticated route is requested
- **WHEN** a crawler requests `/login`, `/app`, `/error`, or another allowlisted non-search application route
- **THEN** the route remains usable and the initial response includes `X-Robots-Tag: noindex, nofollow`

### Requirement: Canonical host MUST be singular
The Global public host MUST use `https://offersteady.com` as the canonical origin and permanently redirect `www.offersteady.com` to the equivalent apex URL.

#### Scenario: Alternate host is requested
- **WHEN** a client requests an HTTPS `www` URL with a path and query
- **THEN** the server returns a permanent redirect to the same path and query on `https://offersteady.com`

### Requirement: Public caching and security MUST remain isolated from realtime traffic
Indexable static HTML and discovery resources MUST use bounded public revalidation caching, fingerprinted assets MUST remain immutable, and API/SSE/WebSocket/authenticated responses MUST retain their existing non-buffered or no-store behavior.

#### Scenario: Static and realtime resources are compared
- **WHEN** deployment verification inspects a public HTML page, a fingerprinted asset, and a realtime/API route
- **THEN** each response has the cache/buffering behavior appropriate to its class and no public cache applies to user-specific or streaming data

### Requirement: Production release MUST be regression-gated
The Global Web release MUST fail verification if public metadata, status, schema, sitemap, GEO MIME/body, prohibited copy, route isolation, or existing application access regresses.

#### Scenario: Candidate build is verified
- **WHEN** the release verifier checks source, build output, inner Nginx, and production URLs
- **THEN** all indexable routes, application noindex routes, unknown 404 behavior, GEO resources, sitemap entries, and core Global health/login routes pass before completion is reported

