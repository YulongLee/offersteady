## ADDED Requirements

### Requirement: Beta runtime is isolated from production
The system MUST run the realtime optimization Beta as a separate deployment project with dedicated ports, PostgreSQL and Redis volumes, environment configuration, storage namespace, and runtime identity. Beta MUST NOT read or mutate production user, interview, payment, transcript, material, session, or release-manifest state.

#### Scenario: Beta stack starts
- **WHEN** operators deploy the optimized release for acceptance testing
- **THEN** only Beta containers and Beta-owned data volumes are created or updated and all existing production containers remain running with their current images and configuration

#### Scenario: Beta test data is required
- **WHEN** acceptance testing needs users, interviews, or materials
- **THEN** the system uses synthetic Beta data and does not copy production personal data into the Beta database

### Requirement: Beta has a distinct HTTPS entrypoint
The Beta Web and API SHALL be exposed through `https://beta.mianshiwen.cn` with a valid HTTPS certificate and Beta-specific CORS/session configuration. The production domain route MUST remain unchanged until explicit promotion approval.

#### Scenario: Tester opens Beta URL
- **WHEN** a tester visits `https://beta.mianshiwen.cn`
- **THEN** Web assets, API, SSE, and WebSocket traffic resolve only to the Beta stack over HTTPS

#### Scenario: Production is checked during Beta testing
- **WHEN** Beta is deployed or restarted
- **THEN** `https://mianshiwen.cn` continues serving the previously deployed production build and health checks without a route switch

### Requirement: End-to-end Beta uses a separately identified companion
The system MUST provide a signed test companion whose name, bundle/application identity, API origin, and update manifest clearly identify Beta. The production companion bundle identifier, packages, and public manifest MUST remain unchanged during Beta acceptance.

#### Scenario: Beta companion captures audio
- **WHEN** the tester starts a Beta interview using the Beta companion
- **THEN** its authentication, audio frames, terminal acknowledgements, and health events are sent only to the Beta API

#### Scenario: Production companion remains installed
- **WHEN** a tester installs the Beta companion beside the production companion on macOS
- **THEN** the two applications have distinct identities and permissions and neither silently changes the other's configured service origin

### Requirement: Beta cannot perform production commercial side effects
The Beta environment MUST disable real payment callbacks, production release publication, and any action that could grant production membership or points. External provider use MUST be explicitly configured and observable as Beta traffic.

#### Scenario: Tester opens billing in Beta
- **WHEN** a tester reaches a payment action in the Beta environment
- **THEN** the system blocks production payment creation/callback effects and clearly treats the operation as unavailable or test-only

### Requirement: Promotion requires explicit approval and immutable artifacts
Production SHALL NOT switch to the optimized release until the automated release gates pass and the user explicitly approves either the observed Beta behavior or the resource-constrained direct-canary exception. Promotion MUST use the tested source commit and immutable image/package digests, with the previous production artifacts recorded for rollback. A direct canary MUST deploy the backward-compatible backend before Web, keep new watchdog enforcement disabled initially, verify existing companions, and defer the new companion manifest until server health passes.

#### Scenario: Beta acceptance has not been approved
- **WHEN** automated tests pass but the user has not approved the Beta experience
- **THEN** production routing, containers, feature flags, and companion manifest remain unchanged

#### Scenario: User approves promotion
- **WHEN** the user explicitly approves the tested Beta release
- **THEN** operators promote the recorded artifacts in the compatibility-first order and retain an independently executable rollback to the prior production artifacts

#### Scenario: User declines parallel Beta because the host lacks headroom
- **WHEN** the user explicitly requests local full verification followed by direct production deployment and the server cannot safely host another stack
- **THEN** operators keep Beta stopped, record the production rollback baseline, deploy backend then Web with recovery enforcement disabled, verify existing companions and production health, and only then publish a newly signed companion manifest

### Requirement: Beta resource use cannot degrade production
The Beta deployment MUST have bounded CPU, memory, concurrency, and lifecycle controls. Testing MUST stop or scale down Beta when production health or latency crosses its existing alert thresholds.

#### Scenario: Beta test causes resource pressure
- **WHEN** production CPU, memory, API P95, Redis latency, or database health crosses the configured safety threshold during a Beta test
- **THEN** operators stop or constrain the Beta stack without restarting production services
