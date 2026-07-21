## ADDED Requirements

### Requirement: Production ownership requires authentication

The production backend MUST derive user ownership from a verified access token. It MUST NOT accept a request-supplied user identifier as proof of identity when no authenticated context exists.

#### Scenario: Unauthenticated caller supplies a user identifier
- **WHEN** a production request has no valid access token but contains a `userId`
- **THEN** ownership resolution returns `401` and no user-scoped operation executes

#### Scenario: Development fixture supplies a user identifier
- **WHEN** a development or test request uses an explicit synthetic user identifier without an access token
- **THEN** the compatibility path may resolve that identifier for local verification

### Requirement: Production provider selection fails closed

Production factories for SMS, chat, screenshot vision, realtime ASR, MinerU, embedding, query embedding, and rerank MUST require their real server-side configuration. Missing configuration MUST produce an explicit unavailable/configuration failure and MUST NOT select fake, synthetic, heuristic, or placeholder output.

#### Scenario: Vision credentials are absent in production
- **WHEN** the screenshot vision factory is resolved without its required production endpoint or API key
- **THEN** factory resolution fails without constructing a synthetic vision gateway

#### Scenario: Embedding credentials are absent in development
- **WHEN** a local development test resolves embedding without remote credentials
- **THEN** it may use the deterministic synthetic adapter

### Requirement: Configuration errors do not expose secrets

Production provider validation errors and logs MUST identify the capability and missing variable names without including configured secret values.

#### Scenario: ASR key is missing
- **WHEN** realtime ASR production validation fails
- **THEN** the error can identify `OFFERSTEADY_REALTIME_ASR_API_KEY` as missing and contains no other credential value
