## ADDED Requirements

### Requirement: The system MUST provide one unified authentication service
The system SHALL provide one unified Authentication Service that owns account registration, login, token issuance, token validation, logout, and authenticated-user retrieval for OfferSteady.

#### Scenario: Authenticated product areas use one identity system
- **WHEN** protected product APIs require an authenticated user
- **THEN** they MUST rely on one shared authentication boundary instead of implementing per-feature login checks

#### Scenario: Authentication remains independent from feature services
- **WHEN** Chat Service, Interview Session, Billing, or other feature services need a user identity
- **THEN** they MUST consume authenticated identity through shared auth boundaries rather than embedding account or password logic

### Requirement: The authentication service MUST support account registration and password login
The system SHALL support first-party account registration and password-based login with secure password hashing and validation so the product has one provider-independent account baseline before external provider login is added.

#### Scenario: New account registers successfully
- **WHEN** a user submits a valid new account identifier and password
- **THEN** the system MUST create one new user account, hash the password, and return a safe authenticated result without exposing the stored hash

#### Scenario: Login credentials are invalid
- **WHEN** a user submits an unknown account identifier or incorrect password
- **THEN** the system MUST reject the login with a generic authentication failure result and MUST NOT reveal whether the account exists

### Requirement: The authentication service MUST issue short-lived access tokens and refresh tokens
The system SHALL issue a short-lived JWT access token plus a refresh token so clients can authenticate API requests while maintaining renewable multi-device sessions.

#### Scenario: Login succeeds
- **WHEN** a user completes a valid login
- **THEN** the system MUST issue one access token and one refresh token associated with that login session

#### Scenario: Access token expires
- **WHEN** a previously issued access token is expired but the refresh token remains valid
- **THEN** the system MUST allow the client to obtain a new access token through the refresh flow without requiring immediate password re-entry

### Requirement: The authentication service MUST validate tokens through a shared middleware boundary
The system SHALL provide one shared token-validation middleware or dependency boundary for protected APIs so authenticated routes can trust user identity, token validity, and session state consistently.

#### Scenario: Protected request carries a valid token
- **WHEN** a protected API request presents a valid active access token
- **THEN** the authentication boundary MUST attach the authenticated user identity and session context to that request

#### Scenario: Protected request carries an invalid token
- **WHEN** a protected API request presents a missing, malformed, revoked, or expired token
- **THEN** the authentication boundary MUST reject the request before feature-specific logic runs

### Requirement: The authentication service MUST support multi-device authenticated sessions
The system SHALL support multiple simultaneous authenticated sessions per account so one user can log in on more than one browser or device without overwriting all prior sessions by default.

#### Scenario: User logs in from a second device
- **WHEN** the same account logs in successfully on another supported device
- **THEN** the system MUST create a separate authenticated session with its own refresh-token lifecycle

#### Scenario: One device logs out
- **WHEN** the user logs out from one authenticated device session
- **THEN** the system MUST revoke that session’s refresh token without automatically revoking every other active device session unless explicitly requested

### Requirement: The authentication service MUST expose current-user information safely
The system SHALL provide one authenticated current-user endpoint or equivalent boundary that returns safe profile and account metadata without exposing password hashes, provider secrets, or internal token material.

#### Scenario: Authenticated client requests current user
- **WHEN** a valid authenticated client asks for current-user information
- **THEN** the system MUST return safe user identity and profile metadata for that account

#### Scenario: Unauthenticated client requests current user
- **WHEN** an unauthenticated or revoked client requests current-user information
- **THEN** the system MUST reject the request and MUST NOT expose private profile data

### Requirement: The authentication service MUST support logout and refresh-token revocation
The system SHALL support logout by revoking the corresponding refresh-token-backed session so the client can no longer renew access after logout.

#### Scenario: User logs out normally
- **WHEN** an authenticated user requests logout for the current session
- **THEN** the system MUST revoke that session’s refresh token and treat subsequent refresh attempts as unauthorized

#### Scenario: Revoked refresh token is reused
- **WHEN** a revoked refresh token is presented again
- **THEN** the system MUST reject the refresh attempt and MUST NOT issue a new access token

### Requirement: The authentication service MUST preserve extension points for WeChat login and future membership
The system SHALL keep core account and session management provider-agnostic so WeChat login, account binding, and future membership or entitlement features can extend the identity model without rewriting first-party authentication contracts.

#### Scenario: External identity provider is added later
- **WHEN** a future WeChat or other identity provider is integrated
- **THEN** the core authentication API and session model MUST remain stable while the provider adapter is added behind the identity boundary

#### Scenario: Future membership features need identity linkage
- **WHEN** a later membership or entitlement feature needs a stable account owner
- **THEN** it MUST be able to reference the same authenticated user identity without changing password or token contracts

### Requirement: The authentication service MUST minimize credential and token exposure
The system SHALL store password hashes only in hashed form, keep signing secrets server-side, minimize token exposure, and exclude passwords, refresh tokens, long-lived provider secrets, and raw hashes from ordinary logs and client-visible payloads.

#### Scenario: Authentication logs are emitted
- **WHEN** the system records authentication events
- **THEN** logs MUST include request metadata, session identifiers, outcome, latency, and error category, but MUST NOT include plaintext passwords, refresh tokens, JWT signing secrets, or password hashes

#### Scenario: Client receives an authenticated result
- **WHEN** the authentication service returns login, registration, or refresh results
- **THEN** the payload MUST expose only the intended token and safe profile data for that client flow rather than internal secret material
