## ADDED Requirements

### Requirement: Global customer registration verifies email before account creation
The Global product SHALL require a valid purpose-bound email verification challenge and an acceptable password before creating a new customer account.

#### Scenario: New customer completes registration
- **WHEN** an unregistered Global email submits the correct unexpired registration code and an acceptable password
- **THEN** the system creates one password-backed user, consumes the challenge, grants the normal Global free entitlement, and returns an authenticated session

#### Scenario: Registration targets an existing account
- **WHEN** registration completion targets an email already bound to a Global user
- **THEN** the system does not create a duplicate user or replace that user's credential and returns a non-enumerating failure

### Requirement: Global customer signs in with email and password
The Global product SHALL make normalized email and password the default customer sign-in method and SHALL not send an email for a successful routine login.

#### Scenario: Valid password login
- **WHEN** a Global customer submits a registered email and its valid password
- **THEN** the system issues the normal access and refresh session credentials for the existing user

#### Scenario: Invalid credentials
- **WHEN** an unknown email or incorrect password is submitted
- **THEN** the system returns the same generic failure contract and applies authentication throttling without revealing whether the account exists

### Requirement: Existing passwordless Global customers can establish a password
The Global product SHALL allow a verified existing email account whose password is not established to set its initial password without changing its user identity or owned data.

#### Scenario: Existing customer sets first password
- **WHEN** an existing passwordless customer completes a valid password-setup email challenge and supplies an acceptable password
- **THEN** the system writes the password credential to the same user ID and returns a normal authenticated session

#### Scenario: Password setup targets an already password-backed account
- **WHEN** a setup request targets an account that already has a password
- **THEN** the system does not replace the credential and directs the customer to sign in or use forgotten-password recovery through a generic response

### Requirement: Password change and recovery are separate secure journeys
The Global product SHALL require the current password for an authenticated password change and SHALL require a purpose-bound email challenge for forgotten-password recovery.

#### Scenario: Authenticated password change
- **WHEN** an authenticated Global customer supplies the valid current password and an acceptable new password
- **THEN** the system stores the new password, revokes other active sessions, keeps the current session active, and emits a security audit event

#### Scenario: Forgotten password recovery
- **WHEN** a customer supplies the correct unexpired password-reset code and an acceptable new password
- **THEN** the system consumes the challenge, replaces the password, revokes all earlier sessions, and issues one fresh authenticated session

#### Scenario: Recovery code is replayed across purposes
- **WHEN** a registration, login, or password-setup code is submitted to password recovery
- **THEN** the system rejects it without changing any credential

### Requirement: Global passwords follow a commercial security baseline
The Backend SHALL store new Global passwords using Argon2id, SHALL accept passwords of at least 15 and up to at least 64 characters, SHALL reject common or compromised choices, and SHALL never persist or log plaintext passwords.

#### Scenario: Weak password is submitted
- **WHEN** registration, setup, change, or recovery receives a password that is too short or blocklisted
- **THEN** the system rejects it with actionable policy feedback and stores no password credential

#### Scenario: Legacy password hash authenticates
- **WHEN** a valid legacy PBKDF2 credential successfully authenticates and its policy is outdated
- **THEN** the system replaces it with the current Argon2id representation before completing login

### Requirement: Global password behavior remains isolated
The new customer password lifecycle SHALL be available only in the Global product edition and SHALL NOT alter domestic phone/SMS authentication or Global Admin authentication.

#### Scenario: Domestic deployment receives Global password request
- **WHEN** a domestic product deployment receives a Global customer password endpoint request
- **THEN** the system rejects the request and preserves all existing domestic authentication behavior

#### Scenario: Global Admin signs in
- **WHEN** a Global Admin uses the separately configured administrator authentication surface
- **THEN** the existing Global Admin authentication behavior remains unchanged
