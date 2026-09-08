## ADDED Requirements

### Requirement: Public pricing is accurate before payment activation
The Global public site SHALL display only Free at $0, Weekly Pro at $19.99 per week, and Monthly Pro at $39.99 per month on `/pricing`. It SHALL offer Start Free for the free plan and SHALL label paid plans Coming Soon without initiating a checkout while payments are disabled.

#### Scenario: Visitor reviews pre-launch pricing
- **WHEN** a visitor opens `/pricing` before Global payments are enabled
- **THEN** the three approved plans and prices are visible and no paid-plan control calls a payment API

### Requirement: Refund policy is independently accessible
The Global public site SHALL provide `/refund-policy` as an independent page and SHALL link that page from the public footer.

#### Scenario: Visitor opens the refund policy
- **WHEN** a visitor follows the Refund Policy footer link
- **THEN** the browser opens a page that explains eligibility, request procedure, response timing, refund processing, subscriptions, and statutory rights

### Requirement: Review pages are crawler-readable without client routing
Direct HTTP requests to `/pricing`, `/terms`, `/privacy`, `/refund-policy`, `/contact`, `/about`, and `/security` SHALL return initial HTML containing a unique page title, meta description, canonical URL, H1, and substantive route-specific body content without requiring JavaScript execution.

#### Scenario: Non-JavaScript crawler requests each review URL
- **WHEN** a crawler directly requests any required review URL and does not run JavaScript
- **THEN** it reads metadata, H1, and body content for that URL rather than the home page

### Requirement: Operator and support details are consistent
Terms, About, and Contact SHALL identify the operator as `杭州临平知界智能技术工作室（个体工商户）`, Hangzhou, China. Contact, Terms, and Privacy SHALL show `contact@oneshowailab.com` as the support email.

#### Scenario: Reviewer compares public disclosures
- **WHEN** a reviewer checks the operator and support details across the required pages
- **THEN** the legal identity, location, and support email are consistent wherever required

### Requirement: Responsible-use disclosures remain visible
The required public pages SHALL preserve applicable statements that AI output is guidance, users must verify every claim, and users must follow interview-organiser rules. Public copy SHALL NOT promote cheating, evasion, anti-detection, or bypassing monitoring.

#### Scenario: Reviewer checks product positioning
- **WHEN** a reviewer reads public product and legal copy
- **THEN** the product is described as responsible guidance grounded in verifiable experience and contains no prohibited evasion claims

### Requirement: Discovery and canonical metadata are coherent
The Global site SHALL publish a robots file that references an HTTPS sitemap. The sitemap SHALL list canonical public URLs, and each required page SHALL declare one matching HTTPS canonical URL.

#### Scenario: Crawler discovers review pages
- **WHEN** a crawler reads `/robots.txt`, `/sitemap.xml`, and a required page
- **THEN** the sitemap is discoverable, the page is listed, and its canonical points to the matching `https://offersteady.com` URL

