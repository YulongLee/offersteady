## ADDED Requirements

### Requirement: SMS authentication SHALL expose phone verification APIs
The system SHALL expose backend APIs for requesting a phone SMS verification code and verifying that code for passwordless registration/login.

#### Scenario: Send verification code
- **WHEN** a client submits a valid mainland China phone number to the send-code API
- **THEN** the backend SHALL create a verification challenge, call the configured SMS provider, and return a safe challenge status without exposing the code

#### Scenario: Invalid phone number
- **WHEN** a client submits an invalid phone number format
- **THEN** the backend SHALL reject the request before calling the SMS provider

### Requirement: Aliyun SMS provider SHALL be server-side only
The system SHALL integrate Aliyun `Dypnsapi` SMS verification through a server-side provider adapter and MUST NOT expose Aliyun AccessKey, AccessKey secret, request signature, template configuration, or verification secrets to the browser.

#### Scenario: Send through Aliyun
- **WHEN** SMS provider mode is configured as Aliyun
- **THEN** the backend SHALL call Aliyun `SendSmsVerifyCode` with the configured sign name, template code, phone number, and provider parameters

#### Scenario: Verify through Aliyun
- **WHEN** a user submits a verification code for an Aliyun-managed challenge
- **THEN** the backend SHALL call Aliyun `CheckSmsVerifyCode` and trust login success only when the provider verification succeeds

### Requirement: Verification success SHALL register or login one user
The system SHALL treat successful phone verification as proof of phone control and SHALL create or login exactly one user account for that normalized phone identity.

#### Scenario: First successful phone verification
- **WHEN** a phone number passes SMS verification and no user is bound to that phone identity
- **THEN** the system SHALL create a new user, bind the phone identity, create an auth session, and return access/refresh tokens

#### Scenario: Existing phone logs in
- **WHEN** a phone number passes SMS verification and a user is already bound to that phone identity
- **THEN** the system SHALL create a new auth session for that user and return access/refresh tokens without creating a duplicate user

### Requirement: SMS authentication SHALL reuse the shared auth session boundary
SMS login SHALL issue the same authenticated result shape used by the existing Authentication Service, including safe user profile, JWT access token, refresh token, and auth session id.

#### Scenario: SMS login succeeds
- **WHEN** SMS verification succeeds
- **THEN** protected APIs SHALL accept the issued access token through the shared authentication dependency

#### Scenario: SMS login session refreshes
- **WHEN** an SMS-created auth session presents a valid refresh token
- **THEN** the refresh endpoint SHALL rotate the refresh token and issue a new access token using the existing session lifecycle

### Requirement: SMS challenge state SHALL be rate limited and auditable
The system SHALL enforce rate limits and attempt limits for SMS sending and verification while recording only redacted metadata.

#### Scenario: Phone sends too frequently
- **WHEN** the same phone identity requests verification codes faster than the configured limit
- **THEN** the backend SHALL reject the request with a rate-limit error and SHALL NOT call the SMS provider

#### Scenario: Verification attempts exceed limit
- **WHEN** a challenge receives too many failed verification attempts
- **THEN** the backend SHALL lock or expire that challenge and require the user to request a new code

### Requirement: SMS authentication SHALL classify provider and business errors
The backend SHALL return stable error codes for user-correctable validation failures, rate limits, expired challenges, invalid codes, and provider outages without leaking provider secrets or raw third-party payloads.

#### Scenario: Provider unavailable
- **WHEN** Aliyun SMS API is unreachable or returns a service failure
- **THEN** the backend SHALL return a provider-unavailable error and record request id, provider code, and latency in redacted logs

#### Scenario: Code is wrong or expired
- **WHEN** provider verification reports an invalid or expired code
- **THEN** the backend SHALL reject login with a verification failure and SHALL NOT issue tokens

### Requirement: Web authentication UI SHALL support SMS registration/login
The Web app SHALL provide a phone-number login/register flow that calls backend SMS APIs and restores authenticated user state from real backend tokens.

#### Scenario: User completes SMS login
- **WHEN** the user enters a phone number, receives a code, submits the correct code, and the backend returns tokens
- **THEN** the Web app SHALL persist the authenticated session and load product pages using that user's identity

#### Scenario: User is not authenticated
- **WHEN** no valid auth session can be restored
- **THEN** protected product areas SHALL require login instead of silently assigning the user to the prototype admin account

### Requirement: Authenticated user id SHALL own commercial product data
The system SHALL use the authenticated user id as the owner for materials, interviews, billing/points, desktop binding, and history operations.

#### Scenario: Authenticated user accesses materials
- **WHEN** an authenticated user opens the material library
- **THEN** the backend SHALL query and mutate materials for that authenticated user id rather than a hardcoded admin identity

#### Scenario: Different users share one browser machine
- **WHEN** user A logs out and user B logs in on the same browser
- **THEN** the Web app and backend SHALL show user B's product data and SHALL NOT expose user A's materials, interviews, points, or history

### Requirement: SMS authentication SHALL be testable without real user data
The system SHALL provide fake or mocked SMS provider tests that use synthetic phone numbers and SHALL isolate real Aliyun integration checks behind explicit environment configuration.

#### Scenario: Unit tests run locally
- **WHEN** backend and frontend tests run without Aliyun credentials
- **THEN** SMS authentication tests SHALL use fake provider behavior and SHALL NOT call real SMS APIs

#### Scenario: Integration verification runs with credentials
- **WHEN** Aliyun SMS credentials and test phone configuration are explicitly provided
- **THEN** the integration verifier SHALL check send/verify readiness and report redacted provider diagnostics
