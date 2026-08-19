## ADDED Requirements

### Requirement: Three engineering guides MUST answer distinct interview intents
The site MUST publish substantive guides for Java backend, frontend, and algorithms. Each MUST provide a direct preparation framework, topic map, engineering trade-offs, failure or correctness checks, visible FAQ, and related canonical resources without duplicating another page's primary purpose.

#### Scenario: Candidate opens an engineering topic from search
- **WHEN** an unauthenticated visitor opens an engineering topic URL
- **THEN** server-delivered HTML provides a complete preparation path without requiring JavaScript, registration, or knowledge of the product

### Requirement: Guidance MUST remain truthful and technically reviewable
Each guide MUST cite official specifications/documentation or university material, distinguish stable concepts from version/implementation choices, show organization reviewer and dates, and MUST NOT present leaked questions, invented project outcomes, or guaranteed interview results.

#### Scenario: Candidate adapts a framework
- **WHEN** a reader prepares an answer or project example
- **THEN** the guide instructs them to use verifiable personal experience and explain assumptions, correctness, measurements, and boundaries

### Requirement: Guides MUST expose SEO, GEO, and maintenance signals
Each guide MUST contain one H1, unique metadata, self-canonical, organization author/reviewer, publication and modification dates, Article and BreadcrumbList JSON-LD, at least five contextual internal links, visible limitations, and a maximum source HTML size of 20 KB.

#### Scenario: Crawler parses an engineering topic
- **WHEN** a crawler retrieves one of the three pages
- **THEN** it can identify intent, ownership, dates, canonical URL, sources, related pages, and limitations from server-delivered HTML

### Requirement: The complete public surface MUST remain release-verified
Released topics MUST be linked from relevant hubs and included in sitemap/GEO sources, with explicit Nginx routes, CSP hashes, source checks, production-build checks, and online smoke coverage for all 30 canonical public pages.

#### Scenario: Engineering topic release is prepared
- **WHEN** deterministic verification runs
- **THEN** it fails on missing routes, links, metadata, structured data, sources, boundaries, discovery entries, or excessive article size before deployment
