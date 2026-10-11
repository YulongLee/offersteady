## ADDED Requirements

### Requirement: Public resource directory

The CN Web experience SHALL expose a public resource directory at `/resources/` that lists the five approved technical reports with category, title, summary, publication date, and a link to each article.

#### Scenario: Visitor opens the resource directory

- **WHEN** an unauthenticated visitor requests `/resources/`
- **THEN** the server returns a static HTML page with a single H1, the five report entries, and no login requirement

#### Scenario: Visitor follows a report entry

- **WHEN** a visitor selects a report from `/resources/`
- **THEN** the browser navigates to that report's stable `/resources/<slug>/` URL

### Requirement: Public report pages

Each approved technical report SHALL be available as a crawlable static HTML page under `/resources/<slug>/` and SHALL contain the approved report body, a unique title and description, one H1, publication metadata, and descriptive internal links to relevant product or guide pages.

#### Scenario: Search crawler reads a report

- **WHEN** a crawler requests an approved report URL without cookies or JavaScript execution
- **THEN** the response contains the report title, substantive body text, canonical URL, and links to related public pages

#### Scenario: Unknown report slug

- **WHEN** a visitor requests a resource slug that is not in the approved report list
- **THEN** the server returns the existing 404 response and does not fall back to an unrelated report or authenticated app page

### Requirement: Search metadata and discovery

The resource directory and every report page SHALL expose self-referencing canonical metadata, `Article` or `WebPage` JSON-LD as appropriate, `BreadcrumbList` JSON-LD, and sitemap entries with the current review date.

#### Scenario: Metadata is present

- **WHEN** a static metadata check parses a resource page
- **THEN** it finds one canonical URL matching the page URL, one H1, valid JSON-LD containing the page URL, and a non-empty description

#### Scenario: Sitemap contains only approved resources

- **WHEN** the sitemap regression check reads `sitemap.xml`
- **THEN** it finds the resource directory and all five approved report URLs, and it does not add authenticated `/app` or `/login` URLs

### Requirement: Homepage resource entry

The public CN homepage SHALL add a visible resource-center link inside the existing “查看更多资源” area and SHALL preserve all existing product, login, payment, interview, and footer links.

#### Scenario: Homepage resource navigation

- **WHEN** a visitor expands “查看更多资源” on the public homepage
- **THEN** the visitor sees a link named “技术报告与资源中心” pointing to `/resources/`, while existing resource links remain available

#### Scenario: Homepage behavior is unchanged

- **WHEN** a visitor uses the existing homepage product, pricing, login, download, or support entry
- **THEN** the existing destination and visible product content remain unchanged apart from the additional resource link

### Requirement: Static delivery and privacy boundary

Resource pages SHALL be delivered without business API calls, authentication state, personal data, audio, screenshot, resume, JD, or payment content, and SHALL reuse the existing public content style without adding a runtime dependency.

#### Scenario: Resource page loads without the backend

- **WHEN** the backend API is unavailable but the Web static asset is available
- **THEN** `/resources/` and approved report pages still render their complete public content

#### Scenario: Sensitive data is absent

- **WHEN** a content and asset scan runs on the resource source and built pages
- **THEN** it finds no service tokens, user identifiers, raw interview media, resumes, or authenticated API endpoints
