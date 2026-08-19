## ADDED Requirements

### Requirement: Every sitemap URL MUST emit distinct canonical server HTML
Each URL in the public sitemap MUST return a successful, indexable HTML response whose canonical URL identifies that same route. The initial HTML MUST provide a route-specific title, description, H1, and crawlable summary without requiring JavaScript.

#### Scenario: Crawler requests the public guide
- **WHEN** a crawler requests `/guide` without executing JavaScript
- **THEN** it receives guide-specific metadata and content with canonical `https://mianshiwen.cn/guide`

#### Scenario: Crawler requests the homepage
- **WHEN** a crawler requests `/`
- **THEN** it receives homepage-specific metadata and content with canonical `https://mianshiwen.cn/`

### Requirement: Public route hydration MUST preserve product behavior
Public route-specific entry documents MUST start the existing React application and MUST NOT change authentication, navigation, support information, or guide interactions.

#### Scenario: User opens the guide with JavaScript enabled
- **WHEN** the browser loads `/guide` and starts React
- **THEN** the existing interactive guide renders and remains usable

### Requirement: Public metadata MUST be truthful and internally consistent
Public structured data, titles, descriptions, and visible crawlable text MUST describe existing product behavior and MUST NOT introduce unverified ratings, reviews, customers, legal entities, or performance claims.

#### Scenario: Search engine parses structured data
- **WHEN** a crawler reads homepage or guide JSON-LD
- **THEN** all referenced URLs and product facts correspond to public routes and existing behavior

### Requirement: Public pages MUST expose crawlable navigation
The initial homepage and guide HTML MUST provide ordinary anchor links connecting the homepage, guide, login, privacy policy, and user agreement as appropriate.

#### Scenario: Crawler follows the public guide link
- **WHEN** a crawler parses the homepage without JavaScript
- **THEN** it can discover `/guide` through an ordinary anchor element

### Requirement: Public and private HTML MUST use different cache policies
Indexable public HTML MUST permit storage with mandatory freshness revalidation. Login, invitation, legal, error, and authenticated application HTML MUST remain `no-store`. Fingerprinted assets MUST retain immutable caching.

#### Scenario: Browser requests an indexable public route
- **WHEN** the browser requests `/` or `/guide`
- **THEN** the response uses a revalidation-friendly public cache policy and is not immutable

#### Scenario: Browser requests a sensitive application route
- **WHEN** the browser requests `/login` or a route under `/app`
- **THEN** the response remains `no-store` and existing index controls remain intact

### Requirement: The release process MUST reject inconsistent sitemap metadata
The deterministic SEO regression check MUST verify every sitemap URL against its corresponding entry document and ingress mapping, including status intent, indexability, unique title and description, self-canonical, H1, crawlable internal links, and expected cache policy.

#### Scenario: A sitemap route points to another canonical
- **WHEN** the release SEO check finds a sitemap URL whose canonical targets a different route
- **THEN** the check fails before deployment

#### Scenario: Production build contains both public entries
- **WHEN** the Web production build completes
- **THEN** the build output contains distinct homepage and guide HTML documents with their expected self-canonicals
