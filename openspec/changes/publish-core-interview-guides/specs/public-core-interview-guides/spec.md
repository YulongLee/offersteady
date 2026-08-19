## ADDED Requirements

### Requirement: Four foundational interview guides MUST answer distinct search intents
The site MUST publish substantive articles for self-introduction, project-experience explanation, technical-interview preparation, and common interview questions. Each article MUST provide a direct answer, actionable framework, common mistakes, visible FAQ, and related canonical resources without duplicating another article's primary purpose.

#### Scenario: Visitor opens a foundational guide
- **WHEN** a visitor arrives from search without an authenticated session
- **THEN** the HTML response provides a complete useful answer and a clear next step without requiring JavaScript or product registration

### Requirement: Examples MUST preserve candidate truthfulness
Templates and examples MUST be labelled as structures to customize and MUST NOT invent a named candidate, employer, project, metric, customer outcome, or guaranteed interview result.

#### Scenario: Visitor uses an answer template
- **WHEN** a visitor reads a self-introduction or project-experience example
- **THEN** the surrounding text directs them to replace placeholders only with facts they can verify and explain under follow-up questions

### Requirement: Articles MUST expose quality and maintenance signals
Each guide MUST contain one H1, unique metadata, self-canonical, organization author/reviewer, publication and modification dates, source boundary, Article and BreadcrumbList JSON-LD, at least five contextual internal links, and a visible product/accuracy boundary.

#### Scenario: Crawler parses an article
- **WHEN** a crawler retrieves one of the four guide pages
- **THEN** it can identify the article intent, ownership, dates, canonical URL, sources, breadcrumb, related pages, and limitations from server-delivered HTML

### Requirement: The complete public surface MUST remain release-verified
The guides MUST be linked from relevant hubs and included in sitemap and GEO sources, with explicit Nginx routes, CSP hashes, source checks, production-build checks, and online smoke coverage for all 24 canonical public pages.

#### Scenario: Guide release is prepared
- **WHEN** deterministic release verification runs
- **THEN** it fails on missing routes, links, metadata, structured data, ownership, sources, boundaries, discovery entries, or excessive article size before deployment
