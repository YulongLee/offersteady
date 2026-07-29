## MODIFIED Requirements

### Requirement: The homepage MUST expose canonical crawlable and shareable metadata

The initial homepage HTML MUST include an absolute self-canonical, one H1, the existing product summary, workflow, pricing model, privacy summary, ordinary internal links, truthful JSON-LD, Open Graph metadata, and a summary-large-image Twitter Card. Social metadata MUST use the canonical apex URL and a 1200x630 raster image. React startup MUST continue to render the approved prototype without changing its product flows.

#### Scenario: Search crawler requests the homepage

- **WHEN** a client reads the homepage response without executing JavaScript
- **THEN** it can identify the homepage topic, canonical URL, product entities, and public product content

#### Scenario: Social crawler requests the homepage

- **WHEN** a social platform reads the homepage document
- **THEN** it receives a title, description, canonical URL, site name, and absolute 1200x630 PNG preview image

### Requirement: Non-public product routes MUST NOT be indexed

Login, error, and authenticated application routes MUST remain directly accessible to users but MUST return an HTTP index-control signal that excludes them from search indexing. They MUST NOT be included in the public sitemap.

#### Scenario: Crawler requests an application route

- **WHEN** a crawler requests `/login`, `/app`, or a known child application route
- **THEN** the response remains successful and includes `X-Robots-Tag: noindex, follow`

#### Scenario: User opens an application route

- **WHEN** a user directly opens the same route
- **THEN** the existing React application and authentication behavior remain unchanged
