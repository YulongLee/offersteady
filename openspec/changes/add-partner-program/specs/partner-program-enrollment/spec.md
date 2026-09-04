## ADDED Requirements

### Requirement: Users explicitly join the partner program
The system SHALL require an authenticated user to accept the current partner agreement before creating a partner profile or enabling cash commission. Joining MUST be idempotent, MUST record the agreement version and timestamp, and MUST NOT silently enroll users who only visit the page.

#### Scenario: User joins for the first time
- **WHEN** an authenticated eligible user accepts the current agreement and joins
- **THEN** the system creates one active partner profile and returns the recorded agreement version and join time

#### Scenario: Join request is retried
- **WHEN** an active partner repeats the same join request
- **THEN** the system returns the existing profile and does not create another profile or link

### Requirement: Each partner receives one safe stable link
The system SHALL create at most one active partner promotion link per user. The public URL MUST use an unguessable URL-safe slug and MUST NOT contain a user ID, phone number, token, device identifier, or server secret.

#### Scenario: Partner opens the dashboard repeatedly
- **WHEN** the same active partner loads the dashboard more than once
- **THEN** every response contains the same active promotion URL unless an administrator has explicitly suspended the profile

### Requirement: Partner attribution is first-level and deterministic
The system SHALL use an eligible promotion click within 30 days before registration to bind a new user to one partner. Only purchases made by that directly attributed user within 90 days after registration SHALL be eligible; purchases by downstream users MUST NOT generate commission.

#### Scenario: Promoted visitor registers and pays in time
- **WHEN** a visitor follows a partner link, registers within 30 days, and has a paid order within 90 days after registration
- **THEN** the order is eligible for that direct partner's commission projection

#### Scenario: Downstream referral pays
- **WHEN** a directly referred user later shares another link and their own visitor pays
- **THEN** the original partner receives no commission for the downstream visitor

### Requirement: Partner dashboard protects referred users
The partner dashboard SHALL expose only aggregate valid visits, registrations, paying users, attributed net receipts, pending commission, available commission and settled commission. It MUST NOT expose referred users' phone numbers, internal IDs, devices, interview content, materials, audio, screenshots, or individual browsing timelines.

#### Scenario: Partner reviews performance
- **WHEN** an authenticated partner loads the dashboard
- **THEN** the system returns aggregate metrics and the partner's own monthly settlement history without any referred-user identity

### Requirement: Partner capability is isolated and reversible
The partner program SHALL be controlled by a server-side feature flag that defaults to disabled. When disabled or unavailable, the homepage and all interview, ASR, answer, screenshot, registration, checkout and payment functions MUST remain available without waiting for partner storage or analytics.

#### Scenario: Partner storage is unavailable during an interview
- **WHEN** partner projection or reporting storage fails while a user is interviewing
- **THEN** the interview continues normally and only the partner report is delayed or unavailable
