## ADDED Requirements

### Requirement: WeChat login SHALL provide a production-compatible scan authorization flow
The system SHALL provide a WeChat scan login flow whose business states, API contracts, and callback lifecycle remain compatible with a formal WeChat Open Platform website login integration, even when the current development phase uses a compatible provider for joint testing.

#### Scenario: Create a login authorization session from the login page
- **WHEN** a user opens the login page and clicks the WeChat login entry
- **THEN** the system SHALL create a short-lived authorization session and return a provider authorization entry that can be rendered as a QR code or controlled authorization window

#### Scenario: Authorization session expires before confirmation
- **WHEN** the user does not complete scanning or authorization before the authorization session expires
- **THEN** the system SHALL mark that authorization session as expired and require the client to request a new authorization session before continuing

### Requirement: WeChat login SHALL complete internal sign-in through provider callback verification
The system SHALL complete login only after the backend verifies the provider callback, validates a one-time state, and resolves one internal OfferSteady user identity.

#### Scenario: Successful callback creates or resolves one OfferSteady user
- **WHEN** the provider callback returns a valid authorization result for a new or existing WeChat identity
- **THEN** the backend SHALL validate the one-time state, resolve one internal User ID, and mark the authorization session as completed

#### Scenario: Replayed or invalid callback is rejected
- **WHEN** the backend receives a repeated callback or a callback whose state is invalid, expired, or already consumed
- **THEN** the backend SHALL reject that callback and SHALL NOT create a new user, new auth session, or new token set

### Requirement: First successful WeChat sign-in SHALL auto-register the user
The system SHALL automatically create one OfferSteady user on first successful WeChat sign-in and reuse the same user on later sign-ins from the same bound provider identity.

#### Scenario: First-time WeChat identity signs in
- **WHEN** a verified WeChat identity signs in and no internal binding exists yet
- **THEN** the system SHALL create one internal user record, persist the provider binding, and continue the login flow without requiring a separate manual registration step

#### Scenario: Existing WeChat identity signs in again
- **WHEN** a verified WeChat identity signs in and an internal binding already exists
- **THEN** the system SHALL reuse the same internal User ID and update the login timestamps without creating a duplicate user

### Requirement: Successful WeChat login SHALL issue OfferSteady access and refresh tokens
The system SHALL issue internal OfferSteady authentication credentials after a successful WeChat login, rather than exposing provider tokens as business credentials.

#### Scenario: Tokens are issued after successful authorization
- **WHEN** the WeChat login flow completes successfully
- **THEN** the system SHALL issue one JWT access token, one refresh token, and one revocable auth session bound to the resolved User ID

#### Scenario: Login state is restored from valid refresh credentials
- **WHEN** a logged-in client presents valid refresh credentials after the access token expires
- **THEN** the system SHALL issue a fresh access token and continue the same internal authenticated session according to refresh-token policy

### Requirement: The authentication API SHALL expose logout and current-user endpoints for WeChat-authenticated accounts
The system SHALL provide current-user retrieval and logout capabilities for users authenticated through the WeChat login flow.

#### Scenario: Current user is queried after WeChat login
- **WHEN** a client with a valid authenticated session requests the current-user endpoint
- **THEN** the system SHALL return the internal User ID, nickname, avatar, login provider, created time, and last login time for that authenticated user

#### Scenario: Logout revokes the active session
- **WHEN** an authenticated user logs out from the current client
- **THEN** the system SHALL revoke the current auth session so that the revoked refresh credentials cannot be used to continue that session

### Requirement: The login provider boundary SHALL remain replaceable
The system SHALL isolate provider-specific login logic behind a provider adapter so that the product can switch from a development-compatible provider to the formal WeChat provider without changing business-layer authentication contracts.

#### Scenario: Provider implementation is swapped
- **WHEN** operators replace the development-compatible provider with the formal WeChat provider
- **THEN** the login page flow, authentication API contract, internal User ID resolution, and downstream business-layer identity contract SHALL remain unchanged
