## ADDED Requirements

### Requirement: Define a v0.1 release boundary
The system SHALL maintain a v0.1 release boundary that identifies which product capabilities are included, which capabilities are MVP-risk items, and which hardening tasks are intentionally deferred.

#### Scenario: Operator reviews release scope
- **WHEN** the operator opens the v0.1 release notes before deployment
- **THEN** the notes list included capabilities, known limitations, deferred hardening tasks, and any user-visible risk that may affect login, materials, interviews, billing, payment, desktop helper, or realtime audio.

#### Scenario: Risk is not acceptable for paid users
- **WHEN** a known limitation can cause paid orders, user identity, material records, or entitlements to be lost after restart
- **THEN** the release boundary marks the limitation as blocking real paid-user launch unless a mitigation or persistence plan is approved.

### Requirement: Protect secrets before GitHub upload
The system MUST prevent server secrets, local `.env` files, API keys, payment keys, OSS credentials, logs with credentials, and real user data from being committed to GitHub.

#### Scenario: Developer prepares GitHub upload
- **WHEN** the developer prepares the v0.1 GitHub push
- **THEN** `.env`, `.env.local`, production secret files, runtime logs, raw real resumes, raw screenshots, and provider keys are excluded, while `.env.example` and documentation describe required variables without secret values.

#### Scenario: Public repository is selected
- **WHEN** the repository is made public or shared outside the core team
- **THEN** the release checklist requires a secret scan and confirms no historical commit contains long-lived credentials.

### Requirement: Deploy with Docker Compose on one Ubuntu server
The v0.1 deployment SHALL support a single Ubuntu 24.04 server pulling code from GitHub and starting Web, Backend, PostgreSQL/pgvector, and Nginx through Docker/Compose.

#### Scenario: Server starts services
- **WHEN** Docker and Git are installed and the repository is pulled on the server
- **THEN** the documented Compose command builds or pulls the required images, creates persistent PostgreSQL storage, starts Backend and Web services, and exposes the configured HTTP entrypoint.

#### Scenario: Service restarts
- **WHEN** the server or Docker daemon restarts
- **THEN** the documented deployment keeps database data in a persistent volume and allows services to be restarted without rebuilding from scratch.

### Requirement: Configure public runtime URLs
The v0.1 deployment MUST configure public Web, Backend, CORS, and frontend API URLs consistently for the chosen server host.

#### Scenario: Web calls Backend through deployment entrypoint
- **WHEN** a user opens the deployed Web page
- **THEN** frontend API requests reach the deployed Backend without duplicate `/api/v1` prefixes, CORS failures, or accidental calls to `127.0.0.1`.

#### Scenario: Server host changes
- **WHEN** the deployment host changes from local development to a public IP or domain
- **THEN** `VITE_API_BASE_URL`, `OFFERSTEADY_PUBLIC_WEB_BASE_URL`, CORS allowed origins, and any OAuth/payment return URLs are updated to the new host before release validation.

### Requirement: Use public payment callback URLs
The v0.1 deployment MUST use public `notify_url` and `return_url` values for码支付 orders, and MUST NOT use local-only callback URLs for real payment validation.

#### Scenario: User buys a product
- **WHEN** a user clicks a product purchase button in the deployed Web page
- **THEN** the Backend creates an OfferSteady order using the server-side product price and returns a码支付 link containing the order number, amount, signed parameters, public `notify_url`, and public `return_url`.

#### Scenario: Payment provider sends notification
- **WHEN** 码支付 sends a payment notification to the deployed `notify_url`
- **THEN** the Backend verifies the signature, matches the internal order, confirms the amount, and credits points or activates the pass exactly once.

#### Scenario: Callback is not reachable
- **WHEN** the payment provider cannot reach the configured `notify_url`
- **THEN** the release checklist marks automatic payment settlement as not ready and prevents claiming that payments auto-arrive.

### Requirement: Verify v0.1 before sealing
The release process MUST run a documented minimum validation suite before labeling the code as v0.1.

#### Scenario: Local validation runs
- **WHEN** the developer prepares the v0.1 seal locally
- **THEN** the documented checks include OpenSpec validation, Web typecheck/build, relevant frontend tests, Backend import or health checks, and a payment-order creation smoke test.

#### Scenario: Server validation runs
- **WHEN** the Docker deployment starts on the server
- **THEN** the operator verifies Web reachability, Backend `/healthz`, billing status API, login path, material page reachability, interview page reachability, and码支付 order creation from the deployed UI.

### Requirement: Provide rollback and operational notes
The v0.1 release SHALL document how to stop services, view logs, restart services, update environment variables, and roll back to the previous known-good commit or tag.

#### Scenario: Deployment fails
- **WHEN** the deployed Web or Backend is not reachable after release
- **THEN** the operator can follow documented commands to inspect Compose logs, stop services, revert to a prior tag or commit, and restart the previous version.

#### Scenario: Configuration changes
- **WHEN** payment URLs, OSS settings, model keys, SMS settings, or CORS origins change
- **THEN** the operator updates the server environment file, restarts affected services, and records the configuration version in the release notes without exposing secret values.
