## ADDED Requirements

### Requirement: Captured frames MUST appear as Web live transcripts
The system SHALL bridge desktop capture frames through backend Realtime Speech to the Web live conversation for the active interview.

#### Scenario: Candidate speaks
- **WHEN** the native runtime emits microphone frames and ASR returns text
- **THEN** the Web live conversation displays the text as “我”

#### Scenario: Interviewer audio plays on computer
- **WHEN** the native runtime emits computer-output frames and ASR returns text
- **THEN** the Web live conversation displays the text as “面试官”

### Requirement: Web live page MUST not depend on stale desktop state
The Web live page SHALL render realtime status and transcripts from the current active session only.

#### Scenario: Previous session has transcripts
- **WHEN** a previous session has desktop transcripts but the current session has no active binding
- **THEN** the current live page does not show those previous transcripts or binding status

### Requirement: Bridge diagnostics MUST identify the failed segment
The system SHALL provide diagnostics that identify whether failure occurred in native capture, desktop-to-backend transport, backend ASR or Web transcript consumption.

#### Scenario: Frames reach backend but Web does not update
- **WHEN** backend records frame receipts and transcripts but the Web page does not display them
- **THEN** diagnostics identify Web consumption as the failing segment
