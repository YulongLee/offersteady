## ADDED Requirements

### Requirement: Global AI discovery resources MUST be valid and consistent
The Global site MUST serve `llms.txt`, `llms-full.txt`, and `public-facts.json` as real discovery resources generated from the public-page catalogue rather than the homepage fallback.

#### Scenario: AI crawler requests concise discovery guidance
- **WHEN** `/llms.txt` is requested
- **THEN** the response is plain text with a site title, description, canonical public links, support route, and responsible-use boundary

#### Scenario: Machine client requests public facts
- **WHEN** `/public-facts.json` is requested
- **THEN** the response is valid JSON with versioned verified facts, canonical URLs, operator, support, pricing status, privacy boundaries, and no secret or user data

### Requirement: Sitemap MUST match the indexable public catalogue
The Global sitemap MUST contain only successful, indexable, self-canonical public URLs and MUST include maintained `lastmod` values.

#### Scenario: Sitemap is built
- **WHEN** the production build generates `sitemap.xml`
- **THEN** every declared URL has a static route document, unique metadata, HTTP 200 expectation, self-canonical, and an accurate `lastmod`

### Requirement: Structured data MUST reflect visible facts
The Global public documents MUST expose valid JSON-LD appropriate to the visible page and MUST NOT introduce ratings, reviews, availability, people, or claims that are not visibly supported.

#### Scenario: Homepage is parsed
- **WHEN** a structured-data parser reads the initial homepage HTML
- **THEN** it finds valid Organization, WebSite, and SoftwareApplication entities using canonical OfferSteady facts

#### Scenario: Public subpage is parsed
- **WHEN** a structured-data parser reads an approved indexable subpage
- **THEN** it finds a WebPage and BreadcrumbList whose names and URLs match visible content and canonical metadata

### Requirement: Social metadata MUST be complete
Every indexable Global public page MUST expose consistent Open Graph and Twitter metadata, and the homepage MUST provide an absolute URL to an approved 1200 by 630 share image.

#### Scenario: Homepage link is shared
- **WHEN** a social crawler reads the homepage without JavaScript
- **THEN** it receives title, description, canonical URL, site name, locale, and absolute preview-image metadata

