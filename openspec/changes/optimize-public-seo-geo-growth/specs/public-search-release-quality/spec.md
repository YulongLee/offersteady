## ADDED Requirements

### Requirement: Release verification MUST cover every public discovery surface
The deterministic release check MUST validate sitemap-listed HTML, Nginx route mappings, canonical URLs, metadata, H1 content, crawlable internal links, JSON-LD syntax, robots policy, `llms.txt`, `llms-full.txt`, and the machine-readable public fact document.

#### Scenario: A sitemap page is missing its route mapping
- **WHEN** a sitemap URL has no explicit production ingress mapping or source document
- **THEN** the release check fails before deployment

#### Scenario: A GEO artifact contradicts a public page
- **WHEN** a canonical URL or product fact in a GEO artifact differs from the maintained public HTML contract
- **THEN** the release check fails and identifies the conflicting field

### Requirement: Existing product routes MUST remain outside the public index
Login, invitation, legal, authenticated application, interview, billing, admin, and error routes MUST retain their existing status behavior, cache policy, and search index controls after the public SEO/GEO release.

#### Scenario: Regression suite checks a sensitive route
- **WHEN** the release suite requests a login or authenticated application route
- **THEN** it remains non-cacheable and excluded from search results without changing its product behavior

### Requirement: Unknown public paths MUST continue to return a real not-found response
Adding new public routes MUST NOT widen the SPA or Nginx fallback to serve indexable homepage content for arbitrary unknown paths.

#### Scenario: Crawler requests an unrecognized topic path
- **WHEN** a crawler requests a path not present in the explicit public or product route registry
- **THEN** it receives HTTP 404 and noindex content rather than a public topic or homepage document
