## ADDED Requirements

### Requirement: Dysmsapi provider SHALL send login codes through approved template
When configured as `aliyun-dysmsapi`, the backend SHALL call Aliyun `Dysmsapi SendSms` with the configured phone number, sign name, template code, and a six-digit `code` template parameter.

#### Scenario: Send succeeds
- **WHEN** a valid mainland phone requests a login code and Aliyun accepts the message
- **THEN** the backend SHALL return the existing safe challenge response without exposing the generated code

#### Scenario: Provider rejects the message
- **WHEN** Aliyun rejects the sign, template, credential, permission, or frequency limit
- **THEN** the backend SHALL record redacted diagnostics and return a stable provider error without persisting the plaintext code

#### Scenario: Provider frequency limit is reached
- **WHEN** Aliyun returns a message-frequency limit response
- **THEN** the backend SHALL return a retryable 429 response with a frequency-limit message instead of reporting the whole SMS service as unavailable

### Requirement: Server-generated codes MUST be stored only as a digest
The backend MUST generate codes using a cryptographically secure random source and MUST persist only an HMAC-SHA256 digest derived with a server-only pepper.

#### Scenario: Challenge is inspected
- **WHEN** a Dysmsapi challenge is stored or read from PostgreSQL
- **THEN** neither the verification code nor a reversible representation of it SHALL be present

### Requirement: Dysmsapi codes SHALL be verified locally and safely
The backend SHALL verify a submitted code using constant-time digest comparison while enforcing the existing challenge phone binding, expiry, attempt limit, and consumed state.

#### Scenario: Correct code is submitted
- **WHEN** the submitted code digest matches an active, unexpired challenge
- **THEN** the system SHALL mark the challenge verified and execute the existing register-or-login flow exactly once

#### Scenario: Wrong code is submitted
- **WHEN** the submitted code digest does not match
- **THEN** the system SHALL increment the attempt count, return the existing user-correctable error, and issue no authentication tokens

### Requirement: Existing Dypnsapi mode SHALL remain available for rollback
The system SHALL keep the existing `aliyun` provider behavior while adding the explicit `aliyun-dysmsapi` mode.

#### Scenario: Production rolls back provider mode
- **WHEN** deployment restores the previous Dypnsapi environment values
- **THEN** the backend SHALL use `SendSmsVerifyCode` and `CheckSmsVerifyCode` without requiring a code digest
