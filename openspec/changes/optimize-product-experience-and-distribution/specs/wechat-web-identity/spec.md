## ADDED Requirements

### Requirement: User can authenticate through a server-mediated WeChat flow
The system SHALL provide a WeChat login and registration action when a configured WeChat identity provider is available. Authorization-code exchange and provider secrets MUST remain server-side, and every flow MUST validate a short-lived single-use state value.

#### Scenario: New user completes WeChat authorization
- **WHEN** an unbound WeChat identity completes a valid authorization flow
- **THEN** the system creates one OfferSteady account, binds the provider identity and starts an authenticated session

#### Scenario: Authorization state is invalid or replayed
- **WHEN** a callback contains an expired, mismatched or previously consumed state value
- **THEN** the system rejects the login without creating, binding or merging an account

### Requirement: Existing users can bind WeChat without silent account collision
An authenticated user SHALL be able to bind an unclaimed WeChat identity after reauthentication. If the identity already belongs to another account, the system MUST block silent reassignment and require an explicit verified merge or recovery process.

#### Scenario: User binds an unused WeChat identity
- **WHEN** an authenticated user reauthenticates and authorizes an unused WeChat identity
- **THEN** the system binds it to the current account and records a security audit event

#### Scenario: WeChat identity already belongs to another account
- **WHEN** a user attempts to bind a WeChat identity owned by another account
- **THEN** the system preserves both accounts and directs the user to verified account recovery or merge

### Requirement: Account recovery survives identity-provider changes
The system SHALL prevent a user from removing their last verified recovery method. WeChat profile fields SHALL be treated as display data rather than stable account keys, and logs MUST redact authorization codes, provider tokens and subject identifiers.

#### Scenario: User tries to unbind the only login method
- **WHEN** WeChat is the user's only verified login or recovery method
- **THEN** the system requires another verified method before completing the unbind operation

#### Scenario: WeChat provider is temporarily unavailable
- **WHEN** the provider cannot complete authorization
- **THEN** the login page preserves non-WeChat recovery options and shows a retryable error without exposing provider details

