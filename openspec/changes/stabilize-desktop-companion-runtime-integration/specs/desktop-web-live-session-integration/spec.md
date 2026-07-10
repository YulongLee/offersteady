## ADDED Requirements

### Requirement: Web machine-code binding MUST update companion connection state
The system SHALL persist Web machine-code binding in the backend and expose it to the desktop companion through runtime status.

#### Scenario: User binds machine code during preparation
- **WHEN** the Web app validates a 6-digit machine code for an interview session
- **THEN** the backend stores the binding and the companion status changes from unbound to bound after its next status sync

#### Scenario: Machine code does not exist
- **WHEN** the Web app attempts to bind a machine code that has not been registered by an open companion
- **THEN** the backend rejects the binding and the Web app keeps the user on the preparation step with the existing error behavior

### Requirement: Starting the interview MUST enable companion publishing
The system SHALL only allow the companion to publish realtime speech after the bound interview session is live.

#### Scenario: Bound interview starts
- **WHEN** the Web app starts a session that is bound to the companion machine code
- **THEN** the companion sees `sessionLive=true`, creates source publishers, and begins publishing available audio frames

#### Scenario: Bound interview has not started
- **WHEN** the session is still in preparation state
- **THEN** the companion remains connected but does not publish realtime audio frames

### Requirement: Live conversation MUST consume backend transcripts
The Web live conversation SHALL display transcript events returned by the backend Realtime Speech APIs for the active interview session.

#### Scenario: Candidate speech transcript is available
- **WHEN** backend stores a microphone transcript for the active session
- **THEN** the Web live conversation displays it as “我”

#### Scenario: Interviewer speech transcript is available
- **WHEN** backend stores a system-output transcript for the active session
- **THEN** the Web live conversation displays it as “面试官”

### Requirement: Quick answer MUST use recent interviewer transcript when no manual question is provided
The system SHALL allow quick answer to derive the answer question from the most recent complete interviewer transcript when the manual input is empty.

#### Scenario: User clicks quick answer after interviewer speaks
- **WHEN** the live page has a recent final “面试官” transcript and the manual question input is empty
- **THEN** quick answer uses that transcript as the question source

#### Scenario: No interviewer transcript exists
- **WHEN** the user clicks quick answer without manual input and without a recent final interviewer transcript
- **THEN** the system reports that no answerable interviewer question is available and does not fabricate a question
