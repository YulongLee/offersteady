## ADDED Requirements

### Requirement: Three AI topic guides MUST answer distinct technical interview intents
The site MUST publish substantive guides for large language models, retrieval-augmented generation, and AI Agents. Each guide MUST define its system boundary, map common interview questions, explain components and trade-offs, include failure diagnosis and evaluation, and provide a visible FAQ without duplicating another guide's primary purpose.

#### Scenario: Candidate opens an AI topic from search
- **WHEN** an unauthenticated visitor opens an AI topic URL
- **THEN** server-delivered HTML provides a complete technical preparation path and related canonical resources without requiring JavaScript or registration

### Requirement: Technical claims MUST be reviewable and provider-neutral
Each guide MUST cite primary papers, standards, or official documentation; distinguish stable concepts from implementation choices; show organization reviewer and dates; and MUST NOT present unverifiable benchmarks, vendor claims, leaked questions, or guaranteed interview results.

#### Scenario: Reader evaluates a technical statement
- **WHEN** a guide explains model behavior, retrieval quality, orchestration, or risk
- **THEN** the page provides an appropriate source boundary and enough context to avoid treating one implementation as a universal rule

### Requirement: Guides MUST expose SEO, GEO, and maintenance signals
Each guide MUST contain one H1, unique metadata, self-canonical, organization author/reviewer, publication and modification dates, Article and BreadcrumbList JSON-LD, at least five contextual internal links, visible limitations, and a maximum source HTML size of 20 KB.

#### Scenario: Crawler parses an AI topic
- **WHEN** a crawler retrieves one of the three pages
- **THEN** it can identify the topic, ownership, dates, canonical URL, sources, related pages, and limitations from server-delivered HTML

### Requirement: The complete public surface MUST remain release-verified
Released AI topics MUST be linked from relevant hubs and included in sitemap/GEO sources, with explicit Nginx routes, CSP hashes, source checks, production-build checks, and online smoke coverage for all 27 canonical public pages.

#### Scenario: Topic release is prepared
- **WHEN** deterministic release verification runs
- **THEN** it fails on missing routes, links, metadata, structured data, sources, boundaries, discovery entries, or excessive article size before deployment
