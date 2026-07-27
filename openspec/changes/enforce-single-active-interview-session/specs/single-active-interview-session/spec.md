## ADDED Requirements

### Requirement: Preparation detects another live interview
The system SHALL query the authoritative backend for another live interview owned by the current user before allowing desktop binding or interview start.

#### Scenario: Another live interview exists
- **WHEN** a user opens preparation for a different session while another session is live
- **THEN** the page displays the live interview title and blocks desktop binding and starting until the conflict is resolved

#### Scenario: No other live interview exists
- **WHEN** a user opens preparation and no different live session exists
- **THEN** the existing material selection and desktop connection flow remains available

### Requirement: User explicitly chooses how to resolve the conflict
The system SHALL allow the user to continue the existing live interview or explicitly end it before preparing the new interview.

#### Scenario: Continue previous interview
- **WHEN** the user selects continue previous interview
- **THEN** the page navigates to that live session without ending it or binding the new session

#### Scenario: End previous interview
- **WHEN** the user confirms ending the displayed previous interview
- **THEN** the backend ends that session and unblocks device selection for the current preparation page

#### Scenario: Conflict changed concurrently
- **WHEN** the expected previous session is no longer the authoritative live session
- **THEN** the backend rejects the takeover and the page refreshes the conflict instead of ending an unrelated session

### Requirement: Backend enforces one live session per user
The backend MUST reject starting or binding a second session when another live session exists and no explicit takeover has completed.

#### Scenario: Client bypasses preparation
- **WHEN** a client directly starts or binds a new session while another session is live
- **THEN** the backend returns a conflict response and preserves the existing live session

### Requirement: Takeover retires the old realtime runtime
The system SHALL retire all realtime resources associated with sessions ended by takeover.

#### Scenario: Old session is superseded
- **WHEN** a takeover succeeds
- **THEN** old desktop bindings become stale, publishers close, ASR work queues are cleared, and old web heartbeats are rejected

#### Scenario: Desktop observes binding generation change
- **WHEN** the server assigns a new binding generation or binding ID
- **THEN** the desktop assistant stops the previous publishers before publishing to the new session

### Requirement: Existing product data remains intact
The system MUST preserve ended interview history, material selections, answers, billing records, and desktop permission state during takeover.

#### Scenario: User reviews the ended interview
- **WHEN** the user opens history after switching to a new interview
- **THEN** the previous interview and its persisted review data remain available
