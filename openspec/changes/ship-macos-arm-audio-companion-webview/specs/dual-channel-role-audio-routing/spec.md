## ADDED Requirements

### Requirement: Audio source MUST determine the visible role
The system SHALL map local microphone/headset audio to the visible role “我” and computer/system audio to the visible role “面试官” without exposing additional role labels.

#### Scenario: Microphone transcript arrives
- **WHEN** a finalized transcript segment is produced from a microphone or headset source
- **THEN** the live conversation displays it as “我”

#### Scenario: System-audio transcript arrives
- **WHEN** a finalized transcript segment is produced from a system-audio source
- **THEN** the live conversation displays it as “面试官”

### Requirement: Mixed or untrusted audio MUST degrade safely
The system MUST suspend automatic answer triggering when it cannot trust source separation and SHALL keep manual question entry available.

#### Scenario: Source is mixed
- **WHEN** a transcript segment comes from a mixed, missing, disconnected, or incompatible source
- **THEN** the system shows an audio-source degraded state and does not invent a third role

#### Scenario: Source is unavailable during capture
- **WHEN** one expected source disconnects during an interview
- **THEN** the system reports the source loss and prevents automatic answers based on untrusted audio until the source recovers

### Requirement: Only interviewer audio MAY trigger automatic answers
The system SHALL run automatic question detection only on final, sufficiently complete system-audio interviewer transcript spans.

#### Scenario: Interviewer asks a clear question
- **WHEN** a final system-audio transcript contains a complete high-confidence interviewer question
- **THEN** the system creates one confirmed question event and may invoke Chat Service once for that question version

#### Scenario: Candidate speaks
- **WHEN** a microphone/headset transcript contains a candidate statement or question
- **THEN** the system displays it as “我” and does not trigger an automatic answer

### Requirement: Duplicate and echo transcripts MUST be isolated
The system MUST prevent repeated or echoed text across microphone and system sources from creating duplicate visible questions or duplicate answer tasks.

#### Scenario: Same text appears in both sources
- **WHEN** echo or duplicated audio causes similar text to appear in both microphone and system-audio streams within the de-duplication window
- **THEN** the system keeps the role-specific transcript display but creates at most one answerable interviewer question

### Requirement: Transcript events MUST preserve source metadata
Realtime transcript events SHALL include session id, source id, source kind, role, revision, time range, finality, overlap, and confidence metadata needed by Web rendering and question detection.

#### Scenario: Interim transcript is revised
- **WHEN** ASR revises an in-progress transcript segment
- **THEN** the system updates the same segment revision rather than adding a duplicate visible row

#### Scenario: Final transcript is emitted
- **WHEN** ASR marks a segment as final
- **THEN** downstream question detection can consume it according to the source role policy
