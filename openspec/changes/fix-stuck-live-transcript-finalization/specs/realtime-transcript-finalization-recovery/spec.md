## ADDED Requirements

### Requirement: Interviewer channel remains authoritative during cross-channel echo

The system SHALL preserve and finalize a system-audio transcript when a near-simultaneous microphone transcript contains the same speech, regardless of which channel publishes its final result first.

#### Scenario: Microphone echo final arrives before interviewer final

- **WHEN** a system-audio partial is followed by a matching microphone final and then a matching system-audio final
- **THEN** the system-audio transcript becomes final and remains eligible for interviewer question detection
- **AND** the microphone copy MUST NOT prevent the interviewer question from triggering its normal answer flow

### Requirement: Suppressed final closes its visible partial

The system MUST move an existing partial for the same segment into a terminal display state whenever its final frame is intentionally suppressed. The terminal reconciliation MUST NOT add session context, detect a question, generate an answer, or consume answer points for the suppressed transcript.

#### Scenario: Final is suppressed as a duplicate

- **WHEN** a visible partial has a matching final frame that is suppressed as a nearby duplicate or cross-channel echo
- **THEN** the visible row no longer reports an active transcribing state
- **AND** no answer or billable usage is created from the suppressed record

### Requirement: Abandoned partial does not claim indefinite activity

The live conversation UI SHALL stop presenting a non-final transcript as actively transcribing after the configured stale interval without a newer revision. It MUST distinguish this recovery presentation from a provider-confirmed final.

#### Scenario: Provider final never arrives

- **WHEN** a partial transcript receives no final or newer revision before the stale interval expires
- **THEN** the row is presented as recognition incomplete instead of transcribing
- **AND** the stale partial does not automatically generate an answer or consume points

### Requirement: Normal final transcript behavior remains unchanged

The system SHALL continue to finalize normal microphone and system-audio transcripts, preserve role separation, and automatically answer only eligible finalized interviewer questions.

#### Scenario: Normal interviewer question finalizes

- **WHEN** a system-audio question receives a normal final result without a cross-channel duplicate
- **THEN** the transcript is confirmed and the existing automatic answer flow runs exactly once
