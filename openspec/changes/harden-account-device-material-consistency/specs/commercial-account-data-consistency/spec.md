## ADDED Requirements

### Requirement: Stable account identity and interview history
The system SHALL resolve repeated successful login for the same verified phone identity to the same user record, SHALL create only a new authentication session, and SHALL restore that user's persisted interviews without creating a default interview.

#### Scenario: Existing user logs in again
- **WHEN** a user verifies the same phone identity after logout or on a later day
- **THEN** the backend returns the existing user ID and all non-deleted interviews owned by that user

#### Scenario: Service restarts between logins
- **WHEN** the backend process restarts before an existing user logs in again
- **THEN** the user's identity and interviews are restored from PostgreSQL rather than process memory

### Requirement: Stable per-installation machine code
The desktop companion SHALL persist one installation device ID and SHALL derive the same machine code across normal launches, account logins, interview bindings, and application upgrades.

#### Scenario: Companion is reopened
- **WHEN** the user quits and reopens the companion without deleting application data or explicitly resetting the device
- **THEN** the displayed device ID and machine code remain unchanged

### Requirement: Real material summary
The Web application SHALL calculate the general material summary from the authenticated user's backend material records and SHALL NOT display hard-coded counts or connection state.

#### Scenario: User has mixed material states
- **WHEN** the backend returns ready, processing, failed, and deleted resume, JD, and knowledge records
- **THEN** the dashboard displays counts derived from non-deleted records and distinguishes ready from processing materials

#### Scenario: User has no materials
- **WHEN** the authenticated user has no non-deleted material records
- **THEN** the dashboard displays zero ready materials and directs the user to manage materials

### Requirement: Fail-closed commercial persistence
The production backend MUST use PostgreSQL for account, interview, and material metadata and OSS for uploaded file bytes, and MUST NOT silently fall back to in-memory storage when a required dependency is unavailable.

#### Scenario: Production database is unavailable
- **WHEN** a production repository cannot initialize or persist a record
- **THEN** the request fails with an observable backend error and no success response is returned

#### Scenario: Material upload persistence succeeds
- **WHEN** a user uploads a supported material and OSS storage plus database registration both succeed
- **THEN** the material appears for the same user after page refresh and backend restart

#### Scenario: OSS write fails
- **WHEN** the backend cannot persist the uploaded bytes to OSS
- **THEN** the upload is reported as failed and no ready material is presented to the user
