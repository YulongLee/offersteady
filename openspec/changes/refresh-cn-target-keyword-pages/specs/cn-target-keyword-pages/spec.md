## ADDED Requirements

### Requirement: Four existing pages SHALL have distinct search intent
The CN public homepage, realtime feature page, existing programmer feature URL and pricing page SHALL retain their URLs, one primary H1 and self canonical. They SHALL respectively explain the product, realtime workflow, technical interview use and price/benefits using natural wording rather than duplicate keyword pages.

#### Scenario: Visitor compares page roles
- **WHEN** a visitor reads the four pages without logging in
- **THEN** the homepage explains resume/JD context and suitable scenarios, realtime page explains question recognition and answer suggestions, programmer page includes concrete project and code verification examples, and pricing page explains membership and points
- **AND** descriptive internal links connect the corresponding pages

### Requirement: Examples and benefits SHALL reflect verified boundaries
All added examples MUST be labeled synthetic and distinguish supplied facts from suggested structure. No fabricated experiences, guaranteed speed, ranking gains or interview outcomes SHALL be claimed. Existing commercial data generation and checkout links MUST remain.

#### Scenario: Visitor reads CN special-feature benefits
- **WHEN** a visitor opens pricing
- **THEN** valid time members are described as receiving three resume optimizations and one mock interview per Beijing calendar day
- **AND** nonmembers or excess usage cost 100 points per optimization/session, mock sessions end automatically after 60 minutes from start
- **AND** these statements do not alter actual billing behavior or the existing product catalog

### Requirement: Candidate SHALL preserve deployed functionality
Changes MUST originate from release-cn-20261022.1 and preserve the sealed deployed Web app, non-target pages and existing app routes including mock interview, resume optimizer and written multi-screen mode. A general source build MUST NOT be treated as deployed-equivalent without comparison.

#### Scenario: Local candidate is reviewed
- **WHEN** the candidate is assembled and served locally
- **THEN** only approved public-page content and supporting assets/SEO facts differ from the sealed Web baseline
- **AND** automated content/link/HTML checks and desktop/mobile visual inspection are recorded
- **AND** no production write, deployment, provider model call or Git push occurs

### Requirement: Authorized CN publication SHALL be a protected Web-only increment
After explicit deployment authorization the release MUST verify actual running Web image, static inventory and Nginx; refresh public pricing; preserve existing business resources and module identity through graph-aware versioned assets; and retain a verified rollback. Backend, worker, Admin, Global, companion, user data and billing behavior MUST remain unchanged.

#### Scenario: Protected work is present
- **WHEN** preparation or cutover checks find any protected active interview, preparation, lease, audio, answer, material, optimizer or financial work
- **THEN** the original service continues without terminating users or weakening gates, except the explicitly authorized one-off existing-preparation-page scenario below
- **AND** the release waits until repeated checks safely pass

#### Scenario: Web-only release is verified
- **WHEN** both baseline and repeated gates pass and the prepared Web increment is installed
- **THEN** all old immutable assets remain byte-identical and all new module references resolve consistently
- **AND** public content, current prices, canonical and exact CSP are verified alongside existing ordinary/mock/written/resume routes and downloads
- **AND** failures restore the retained original Web and preserve all non-target components and private configuration

#### Scenario: Human explicitly permits the single existing preparation page to remain online
- **WHEN** the human explicitly authorizes immediate Web-only deployment despite the known existing preparation page and the one-off CLI flag is supplied
- **THEN** exactly one existing preparation-page lease alone MAY be tolerated for this release while its raw count and the exception are recorded
- **AND** recent preparing sessions, a second preparation lease, live/mock sessions, audio, publishers, unfinished tasks, material/financial work, unknown states or read failures MUST still block
- **AND** no preparation page, session, lease or user data is ended, cleared or modified
