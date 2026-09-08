## ADDED Requirements

### Requirement: Global user authenticates with a verified email address
The Global product SHALL provide an English email verification-code journey that creates a new account on the first successful verification and signs in an existing account on later successful verifications.

#### Scenario: New email registration
- **WHEN** a Global visitor submits a valid email address and the correct unexpired verification code
- **THEN** the system creates one email-bound user and returns the normal access and refresh session credentials

#### Scenario: Existing email sign-in
- **WHEN** an existing Global user verifies the same normalized email address
- **THEN** the system reuses that user account and creates a new authenticated session

### Requirement: Email challenge is secure and one-time
The Backend SHALL persist an expiring, one-time challenge without storing the raw verification code and SHALL enforce resend, daily-send, and verification-attempt limits.

#### Scenario: Valid code is consumed once
- **WHEN** a valid code is successfully verified
- **THEN** the challenge becomes verified and cannot be used to create another session

#### Scenario: Invalid attempts reach the limit
- **WHEN** a user submits invalid codes until the configured attempt limit is reached
- **THEN** the challenge becomes locked and later attempts are rejected

#### Scenario: Challenge expires
- **WHEN** a code is submitted after the configured expiry time
- **THEN** the system rejects it without authenticating the user

#### Scenario: Send limit applies
- **WHEN** an address exceeds the configured resend interval or daily limit
- **THEN** the system rejects the new send request without invoking the delivery provider

### Requirement: Email delivery is replaceable and production-safe
The Backend SHALL deliver codes through a server-side provider adapter, SHALL keep provider credentials out of clients and logs, and SHALL fail closed when production email authentication is enabled without a valid provider configuration.

#### Scenario: Test environment uses deterministic provider
- **WHEN** automated tests enable email authentication with the fake provider
- **THEN** the system can exercise the complete flow without sending a real email

#### Scenario: Production configuration is incomplete
- **WHEN** production enables email authentication without the required approved provider, sender, credential, or code-pepper settings
- **THEN** the application refuses to activate the email delivery path and does not fall back to the fake provider

### Requirement: Global authentication UI is email-first and English
The Global Web SHALL request an email address and verification code in English, SHALL show sending, cooldown, validation, expiry, and failure states, and SHALL not present phone/SMS as the Global customer login method.

#### Scenario: Visitor requests a code
- **WHEN** a visitor enters a valid email and selects the send-code action
- **THEN** the Global Web submits the email request, displays a masked destination confirmation, and starts the resend cooldown

#### Scenario: Visitor enters invalid email
- **WHEN** a visitor submits an invalid email address
- **THEN** the Global Web displays an English validation error and does not call the send-code endpoint

### Requirement: Domestic authentication remains isolated
The email change SHALL NOT alter the domestic Web phone UI, SMS endpoints, SMS provider configuration, or domestic user and session data.

#### Scenario: Domestic application is built
- **WHEN** the domestic Web and Backend run with email authentication disabled
- **THEN** the existing phone/SMS journey continues with its prior API contract and behavior

#### Scenario: Global email account is created
- **WHEN** a Global user completes email authentication
- **THEN** the account, challenge, and session exist only in the Global deployment database and secrets remain only in Global server configuration
