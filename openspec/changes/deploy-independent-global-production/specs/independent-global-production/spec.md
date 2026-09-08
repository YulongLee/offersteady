## ADDED Requirements

### Requirement: Dedicated Global hostname and HTTPS entrypoint
The Global production application SHALL be served from `https://offersteady.com` and `https://www.offersteady.com` with a valid certificate, SHALL route API traffic through same-origin `/api`, and SHALL NOT require a public Global API subdomain.

#### Scenario: Visitor opens the Global site
- **WHEN** a visitor opens either approved Global hostname
- **THEN** the request is served over valid HTTPS by the Global Web application
- **AND** application API calls remain same-origin

### Requirement: Runtime and data isolation
The Global deployment SHALL use its own deployment namespace, PostgreSQL database and volume, Redis instance and volume, application secrets, release marker, and rollback artifacts. It SHALL NOT connect to the Chinese production database or Redis instance.

#### Scenario: Global services start
- **WHEN** the Global production stack starts
- **THEN** every stateful dependency resolves within the Global-only container network
- **AND** no domestic production hostname, database address, Redis address, or release volume is used

### Requirement: Existing workloads remain unchanged
Deployment SHALL preserve all pre-existing services on the overseas host and SHALL make no change to the Chinese production host, `mianshiwen.cn`, or domestic data.

#### Scenario: Global release is installed
- **WHEN** the deployment completes or rolls back
- **THEN** existing overseas Nginx virtual hosts and processes continue serving their original domains
- **AND** the domestic production host has received no deployment command

### Requirement: Safe Global product behavior
The public Global Web application SHALL present English product flows and SHALL create Global interview sessions with an English locale. International commerce SHALL remain unavailable until its provider, currency, tax, refund, and legal behavior are approved.

#### Scenario: User enters a Global interview flow
- **WHEN** the user creates and starts an interview from the Global application
- **THEN** the user-facing workflow is English
- **AND** the session locale is a supported Global English locale

#### Scenario: User opens billing before international commerce approval
- **WHEN** Global commerce is disabled
- **THEN** the application does not create a domestic or international payment order
- **AND** it clearly identifies billing as unavailable for the current launch stage

### Requirement: Server-side secret and privacy boundaries
Private provider and application credentials SHALL remain server-side with restricted filesystem permissions. Raw interview audio SHALL remain non-persistent by default, and operational verification SHALL NOT print credentials, transcript content, screenshots, or source documents.

#### Scenario: Deployment and health checks run
- **WHEN** operators deploy or verify the Global stack
- **THEN** output contains status and non-sensitive identifiers only
- **AND** secret values and user content are absent

### Requirement: Health checks and recoverable rollout
The Global deployment SHALL verify service health, public routing, the production build manifest, TLS, and domestic-host isolation. It SHALL retain enough versioned configuration and image state to roll back application services without deleting Global PostgreSQL or Redis data.

#### Scenario: New release fails verification
- **WHEN** any required post-deployment health check fails
- **THEN** the operator can restore the preceding Global application release and Nginx configuration
- **AND** Global data volumes are not removed

### Requirement: Commercial readiness remains explicit
The deployment SHALL distinguish technical availability from commercial readiness. International authentication, messaging, AI-region suitability, storage residency, payment, tax, privacy, and legal requirements SHALL be tracked as launch blockers until separately verified.

#### Scenario: Technical deployment succeeds before provider readiness
- **WHEN** the site and core services pass technical checks but one or more international provider requirements remain unresolved
- **THEN** the release is reported as a technical preview rather than a commercial production launch
- **AND** unresolved launch blockers are documented
