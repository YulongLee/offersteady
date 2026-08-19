## ADDED Requirements

### Requirement: Public pages MUST reserve image layout space
Images rendered on public indexable pages MUST declare intrinsic dimensions or an equivalent stable aspect ratio. Below-the-fold images MUST use deferred loading and asynchronous decoding unless measurement proves they are the page LCP element.

#### Scenario: Lighthouse evaluates a public page
- **WHEN** a public page renders at a mobile viewport
- **THEN** image loading does not create avoidable layout shift and non-critical images do not block first paint

### Requirement: Public assets MUST use cache policies appropriate to their sensitivity and versioning
Fingerprint-addressed static assets MUST use long-lived immutable caching. Indexable HTML MUST require freshness revalidation, while login, invitation, authenticated, legal, and error HTML MUST remain non-cacheable and retain existing index controls.

#### Scenario: Client requests a fingerprinted public asset
- **WHEN** a client requests a hashed JavaScript, CSS, font, or optimized image asset
- **THEN** the response permits long-lived immutable caching without changing authenticated response caching

### Requirement: The release MUST enforce public performance budgets
The release verifier MUST fail when public entry payloads or designated public images exceed documented byte budgets, when required image dimensions are absent, or when public-page Lighthouse SEO regresses below 100. Performance score changes MUST be reported from repeated laboratory runs and MUST NOT be presented as field CWV.

#### Scenario: Public image exceeds its release budget
- **WHEN** a designated public image exceeds the approved encoded byte limit
- **THEN** the verification step fails before deployment and reports the asset path and measured size

#### Scenario: Laboratory performance is reported
- **WHEN** Lighthouse is run more than once for a public page
- **THEN** the report uses the median result and labels CrUX, INP, and real-user p75 values unknown unless field data is available
