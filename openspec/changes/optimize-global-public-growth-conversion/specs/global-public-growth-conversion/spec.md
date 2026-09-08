## ADDED Requirements

### Requirement: Public URL canonicalisation MUST preserve campaign attribution
The Global public ingress MUST preserve the complete query string when permanently redirecting an approved trailing-slash URL to its canonical non-slash URL.

#### Scenario: Campaign visitor opens a trailing-slash public URL
- **WHEN** a visitor requests an approved public URL ending in `/` with UTM or other query parameters
- **THEN** the permanent redirect targets the equivalent non-slash canonical URL with every query parameter preserved

### Requirement: Public conversion pages MUST provide a truthful next action
Every high-intent public conversion page MUST provide an actionable route that matches currently available product capabilities and MUST NOT imply that an unavailable payment or installer can be obtained.

#### Scenario: Visitor opens Download before Global installers are published
- **WHEN** a visitor reads `/download` without executing JavaScript
- **THEN** the page exposes a Start Free link to the existing sign-in flow and explains where verified release options will appear without presenting an unapproved installer URL

#### Scenario: Visitor opens Pricing before payment activation
- **WHEN** a visitor reads `/pricing`
- **THEN** Free remains actionable, paid plans remain visibly Coming Soon, and no live paid checkout control is rendered

### Requirement: Public metadata MUST describe each route clearly
Every indexable Global public route MUST expose a unique, route-specific title and meta description that satisfy the checked-in metadata quality limits while retaining a self-canonical URL.

#### Scenario: Public catalogue is built
- **WHEN** the public-page generator validates catalogue metadata
- **THEN** every title and description is non-duplicated, within the approved length range, and represented unchanged in the generated route HTML

### Requirement: Growth content MUST be useful, verified, and readable
Feature, guide, interview-question, and Download pages MUST contain substantive English content for their declared intent, use scannable headings and concise paragraphs, and preserve OfferSteady's responsible-use boundaries.

#### Scenario: Search visitor reads a feature or hub page
- **WHEN** the page is rendered from server-delivered HTML
- **THEN** it explains the workflow, practical use, limitations, and relevant next steps using only verified product facts

#### Scenario: Public copy is scanned before release
- **WHEN** automated and manual copy checks inspect the public catalogue and homepage
- **THEN** the content avoids deceptive-use language, unsupported outcomes, fabricated proof, and claims that conflict with the product contract

### Requirement: Social preview media MUST remain lightweight and valid
The approved homepage social preview image MUST remain 1200 by 630 pixels and MUST stay below the checked-in public-asset size ceiling.

#### Scenario: Global Web build is verified
- **WHEN** the release verifier inspects the generated social preview asset
- **THEN** its dimensions, public path, media type, and byte size satisfy the approved contract

### Requirement: Growth optimisation MUST remain isolated from core services
The change MUST NOT modify the behavior or deployment of Global authentication, interview, written-exam, Companion, ASR, RAG, AI, Backend, database, Redis, Admin, analytics, or payment services, and MUST NOT modify any Chinese production surface.

#### Scenario: Candidate release is deployed
- **WHEN** the overseas release passes its pre-deployment gates and no live Global interview is active
- **THEN** only the Global Web service is replaced and existing application, API, health, realtime, noindex, and 404 contracts continue to pass

### Requirement: Release verification MUST cover the observed regressions
The Global Web release MUST fail verification if campaign queries are lost, `/download` has no available next action, metadata or content quality regresses, the share image exceeds its limit, or core-route isolation changes.

#### Scenario: Candidate build is evaluated
- **WHEN** source, generated output, Nginx behavior, and public-route tests run
- **THEN** all attribution, action, metadata, content, asset, responsible-use, route-isolation, and pre-payment assertions pass before deployment is allowed
