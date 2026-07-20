## ADDED Requirements

### Requirement: Ordered cursor-based delivery
The web live workspace SHALL consume transcript events in cursor order and SHALL store the last applied cursor for the active session.

#### Scenario: New transcript event arrives
- **WHEN** the web consumer receives the next valid cursor
- **THEN** it applies the event and advances its stored cursor

#### Scenario: Duplicate event arrives
- **WHEN** an already applied transcript segment revision is delivered again
- **THEN** the web consumer ignores it without rendering a duplicate line

### Requirement: Automatic reconnect and replay
The web consumer SHALL reconnect automatically after network, page visibility, proxy, or backend interruption and SHALL request events after its last cursor.

#### Scenario: Backend restarts
- **WHEN** the event connection closes during an active interview
- **THEN** the page reconnects with bounded backoff and replays missed retained events without manual machine-code rebinding

#### Scenario: Cursor has expired
- **WHEN** retained events no longer include the requested cursor
- **THEN** the page loads an authoritative session snapshot and resumes from its current cursor

### Requirement: Role and finality presentation
The live workspace SHALL distinguish candidate and interviewer transcripts and SHALL replace interim revisions with final text for the same segment.

#### Scenario: Interim text is finalized
- **WHEN** a final revision arrives for an existing interim segment
- **THEN** the page replaces that segment instead of appending a second conversation entry

### Requirement: Honest degraded state
The web workspace SHALL show the authoritative failing stage and SHALL keep unaffected manual and screenshot functions available.

#### Scenario: ASR provider is degraded
- **WHEN** audio transport is connected but ASR is unavailable
- **THEN** the page reports an ASR-specific degraded state rather than claiming that the microphone is disconnected
