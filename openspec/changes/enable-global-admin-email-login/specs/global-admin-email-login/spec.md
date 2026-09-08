## ADDED Requirements

### Requirement: Global Admin uses verified email login
The Global Admin SHALL request an email address and email verification code, SHALL use the existing Global email authentication endpoints, and SHALL exchange the resulting user access token through the existing Admin session endpoint.

#### Scenario: Approved administrator signs in
- **WHEN** an authorized Global administrator submits the correct unexpired email verification code
- **THEN** the system creates a normal user session followed by an authenticated Admin session

#### Scenario: Unapproved email verifies successfully
- **WHEN** a valid Global email user without an active administrator authorization completes email verification
- **THEN** the Admin session request is rejected and no administrator permission is granted

### Requirement: Global Admin email interface is edition-isolated
The Admin build SHALL render the email login journey only for the Global product edition, while the domestic Admin SHALL retain its existing phone/SMS journey.

#### Scenario: Global Admin build loads
- **WHEN** the Admin application is built with `VITE_PRODUCT_EDITION=global`
- **THEN** it displays email and email-code controls and does not display the phone login control

#### Scenario: Domestic Admin build loads
- **WHEN** the Admin application is built without the Global product edition
- **THEN** it displays the existing Chinese phone/SMS login journey with its prior API behavior

### Requirement: First Global administrator is explicitly bootstrapped
The first Global super administrator MUST be authorized through an audited server-side bootstrap against an already verified user in the isolated Global database. The approved identity MUST NOT be hardcoded as a client privilege bypass or copied from domestic production.

#### Scenario: Approved email user exists
- **WHEN** the operator bootstraps the explicitly approved verified Global email user
- **THEN** exactly one active Global super-administrator authorization is created and no domestic authorization changes

#### Scenario: Approved email user does not exist
- **WHEN** bootstrap is attempted before the email has completed Global verification
- **THEN** bootstrap fails without creating an unverified user or administrator authorization

### Requirement: Authentication secrets remain private
The Global Admin MUST NOT expose email verification codes, provider credentials, access tokens, administrator session tokens, or TOTP enrollment secrets in client constants, source control, application logs, or release documentation.

#### Scenario: Global Admin release is verified
- **WHEN** tests and deployment checks run
- **THEN** they use synthetic identities and report only status, masked destinations, counts, and non-secret identifiers

### Requirement: Public Global Admin remains protected
The public Global Admin hostname SHALL use HTTPS, SHALL remain excluded from indexing and framing, and SHALL return an authentication error for protected Admin APIs when no valid Admin session is supplied.

#### Scenario: Anonymous visitor opens protected API
- **WHEN** an unauthenticated request reaches `/api/v1/admin/session`
- **THEN** the server returns HTTP 401 without revealing administrator data
