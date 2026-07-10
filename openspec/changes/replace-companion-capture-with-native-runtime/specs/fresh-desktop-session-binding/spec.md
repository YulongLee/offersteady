## ADDED Requirements

### Requirement: Desktop binding MUST require fresh Web and desktop heartbeats
The backend SHALL treat a desktop-session binding as active only when both the desktop device heartbeat and the Web session heartbeat are fresh.

#### Scenario: Web page is closed
- **WHEN** the Web page stops sending heartbeat beyond the freshness window
- **THEN** the desktop companion no longer displays the session as actively bound

#### Scenario: Desktop companion is closed
- **WHEN** the desktop companion stops sending heartbeat beyond the freshness window
- **THEN** the Web preparation page reports the machine code as unavailable or disconnected

### Requirement: Latest historical binding MUST NOT be shown as active
The backend MUST NOT return a historical latest binding as active unless it passes freshness, generation and session-state checks.

#### Scenario: Old session remains in repository
- **WHEN** a machine code has an old binding but no current Web heartbeat
- **THEN** desktop pairing status returns unbound or stale rather than “已绑定面试”

#### Scenario: New binding generation is created
- **WHEN** the desktop companion registers a new device generation for the same machine code
- **THEN** old bindings from previous generations are not considered active

### Requirement: Session state MUST control companion publishing
The backend SHALL allow desktop publishing only for a fresh active binding whose session state is live.

#### Scenario: Session is preparing
- **WHEN** the machine code is bound but the interview is still preparing
- **THEN** the companion displays bound-but-not-live and does not publish audio

#### Scenario: Session is ended
- **WHEN** the interview session has ended
- **THEN** the companion stops publishing and clears the active binding state
