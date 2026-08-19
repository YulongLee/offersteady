## ADDED Requirements

### Requirement: The public site MUST expose three distinct content hubs
The site MUST publish server-rendered, unauthenticated pages at `/features`, `/guides`, and `/interview-questions`. Each hub MUST have a distinct primary intent, substantive unique content, one H1, route-specific metadata, a self-canonical URL, and valid WebPage and BreadcrumbList structured data.

#### Scenario: Visitor opens a content hub without JavaScript
- **WHEN** an unauthenticated visitor or crawler requests any of the three hub URLs without executing JavaScript
- **THEN** the server returns HTTP 200 with the complete hub title, explanation, and crawlable child links in the HTML response

### Requirement: Product documentation and editorial guidance MUST remain distinguishable
The navigation and hub copy MUST identify `/guide` as the product usage manual and `/guides` as the editorial interview-guidance directory.

#### Scenario: Visitor chooses between manual and guidance content
- **WHEN** a visitor encounters links to both `/guide` and `/guides`
- **THEN** the visible link labels and nearby descriptions make clear whether the destination explains product operation or interview preparation

### Requirement: Content hubs MUST link only to available canonical resources
Hub cards and navigation MUST link to real HTTP-success public pages and MUST NOT present planned, empty, duplicate, authenticated, or noindex destinations as published editorial resources.

#### Scenario: Release verifier checks hub links
- **WHEN** the release verifier resolves internal hub links against the public route manifest
- **THEN** every promoted child destination has an explicit production route, a self-canonical URL, and indexable substantive content

### Requirement: Discovery sources MUST include the complete hub surface
The sitemap, homepage/public navigation, `llms.txt`, `llms-full.txt`, and `public-facts.json` MUST reference the three hubs consistently, and deterministic source/build checks MUST cover the resulting 20-route canonical surface.

#### Scenario: Release verification compares public discovery sources
- **WHEN** source and production-build verification run before deployment
- **THEN** the checks confirm all three hubs are discoverable, metadata-valid, internally linked, explicitly routed, and represented in the maintained discovery sources

### Requirement: Content hubs MUST preserve product and privacy boundaries
The hubs MUST NOT expose private data or APIs, change authenticated functionality, claim unsupported integrations or outcomes, or present generated examples as verified customers or facts.

#### Scenario: Visitor reads a hub boundary statement
- **WHEN** a visitor evaluates product capabilities or interview content from a hub
- **THEN** the page distinguishes product assistance and educational guidance from guarantees, official platform partnerships, or invented personal experience
