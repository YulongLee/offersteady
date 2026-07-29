## ADDED Requirements

### Requirement: Unknown public paths MUST return a real not-found response

The public ingress MUST serve the SPA entry document only for browser routes implemented by the product. A path that is neither a known browser route, API route, static resource, nor SEO control resource MUST return HTTP 404 and a usable noindex error document.

#### Scenario: Crawler requests an unknown path

- **WHEN** a crawler requests a random path that is not part of the product
- **THEN** the response status is 404 and the response body is not the homepage document

#### Scenario: User opens a supported client route directly

- **WHEN** a user directly opens a supported login, application, preparation, live, or review route
- **THEN** Nginx serves the SPA entry document so the existing React route continues to work

### Requirement: Search control resources MUST use their standard formats

The site MUST publish a plain-text `robots.txt` and a valid XML `sitemap.xml`. The sitemap MUST contain only public canonical URLs that return a successful response.

#### Scenario: Crawler discovers site policy

- **WHEN** a crawler requests `/robots.txt`
- **THEN** it receives plain-text crawl directives and the absolute sitemap URL

#### Scenario: Crawler reads the sitemap

- **WHEN** a crawler requests `/sitemap.xml`
- **THEN** it receives XML containing the apex homepage and no login or application URLs

### Requirement: The homepage MUST expose canonical crawlable content without JavaScript

The initial homepage HTML MUST include an absolute self-canonical, one H1, the existing product summary, workflow, pricing model, privacy summary, ordinary internal links, and truthful JSON-LD. React startup MUST continue to render the approved prototype without changing its product flows.

#### Scenario: Non-JavaScript crawler requests the homepage

- **WHEN** a client reads the homepage response without executing JavaScript
- **THEN** it can identify the homepage topic, product workflow, usage model, privacy boundary, internal login link, canonical URL, and product entities

#### Scenario: Browser runs the application

- **WHEN** the browser loads the same homepage and executes the production JavaScript
- **THEN** the existing React landing page replaces the static snapshot and all existing interactions remain available

### Requirement: The apex host MUST be the canonical public host

Requests to the `www` host MUST permanently redirect to the equivalent apex URL while preserving the path and query string.

#### Scenario: User opens the www host

- **WHEN** a user requests a URL on `www.mianshiwen.cn`
- **THEN** the ingress returns HTTP 308 to the same path and query on `https://mianshiwen.cn`
