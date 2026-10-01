## ADDED Requirements

### Requirement: Public routes render independently of business state
Global public routes and the login form MUST render without waiting for `/api/v1/web/state` or importing the protected workspace entry. Existing public content, layout, links, metadata, and pricing MUST remain unchanged.

#### Scenario: Backend unavailable on public routes
- **WHEN** the business-state API is delayed or fails and a visitor opens the homepage, pricing, or login
- **THEN** the page content or login form is available without requesting business state
- **AND** viewing the page does not start an interview or checkout

### Requirement: Protected workspace remains authenticated
Workspace routes MUST continue to validate sessions and load real backend state before rendering user data. A local session hint MUST NOT grant access. Password login, registration, password setup/reset, logout, nested return destinations, and billing-return redirects MUST remain available.

#### Scenario: Unsigned direct workspace navigation
- **WHEN** an unsigned visitor opens a nested workspace URL
- **THEN** they are redirected to login without downloading workspace code or requesting anonymous business state
- **AND** successful login returns to the intended internal route

#### Scenario: Existing or expired session
- **WHEN** an existing session is restored or rejected
- **THEN** only a validated session can enter the workspace
- **AND** stale restore results cannot override a newer login or display stale account data

### Requirement: Noncritical media is demand loaded
Promotional video sources MUST NOT download before explicit playback intent. Offscreen posters MUST NOT download during initial render. Initial static HTML MUST NOT undo this policy. Videos MUST preserve layout dimensions and keyboard-accessible playback.

#### Scenario: Cold homepage load
- **WHEN** the homepage is loaded at the top without interacting
- **THEN** no promotional MP4 or offscreen video poster is requested by static HTML or React

#### Scenario: Poster visibility and playback
- **WHEN** the visitor approaches a video and activates its play control
- **THEN** its poster can load near the viewport and its video source loads on activation
- **AND** playback remains available without intersection-observer support

### Requirement: Verification and edition isolation
The change MUST be verified with component regressions, type checking, production build inspection, and local browser tests using synthetic API responses. Domestic code, backend, desktop, model, and commercial rules MUST remain unchanged.

#### Scenario: Release candidate review
- **WHEN** the candidate is built and tested
- **THEN** the public entry excludes workspace modules, the existing Global routes remain available, and results distinguish local evidence from unmeasured production performance

#### Scenario: Authorized Web-only production release
- **WHEN** the user authorizes deployment and ordinary/mock interviews and active session work are idle
- **THEN** only Global Web is replaced, preserving its runtime configuration and previous hashed assets
- **AND** all non-Web containers remain unchanged, the prior Web image is available for rollback, and public/protected routes and build identity are verified
