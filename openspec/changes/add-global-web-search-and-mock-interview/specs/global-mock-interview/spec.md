## ADDED Requirements

### Requirement: English practice with existing companion
Global SHALL provide a Mock interview entry below Written Exam, English preparation/workbench/report and Word export. A user SHALL select their ready parsed resume and bind their existing supported companion; microphone permission and device ownership MUST be checked without requiring a new companion release.

#### Scenario: Ready device
- **WHEN** a supported v2 companion is bound and fresh but reports microphone permission as unknown
- **THEN** the page truthfully defers permission confirmation, allows preparation to start, and requires an authenticated microphone audio channel before accepting an answer

### Requirement: Question and audio lifecycle
Each practice SHALL publish at most ten resume/conversation-grounded questions, read with the configured qwen3-tts-instruct-flash-realtime model in English. User action Answer complete advances the round. Only answer-phase microphone audio SHALL be transcribed; question playback/late audio MUST be discarded and no raw audio persisted. Playback animation MUST reflect actual playback.

#### Scenario: User thinks silently
- **WHEN** the user pauses during an answer
- **THEN** no next question is generated until Answer complete is selected

#### Scenario: Exit or disconnect
- **WHEN** the session ends, the control lease expires, or the user leaves
- **THEN** audio, TTS, tasks and controller references are fenced and released; stale callbacks cannot recreate them

### Requirement: Evidence-based report and private export
Reports SHALL save automatically, score only submitted answers, mark partial practice, use literal answer evidence and avoid invented achievements or sensitive-trait inference. No answered questions SHALL produce no score, not zero. Owner-scoped Word export SHALL work without another model request or quota charge.

#### Scenario: Empty or partial practice
- **WHEN** the user finishes with fewer than ten answers
- **THEN** the report identifies the available evidence and does not grade unanswered questions or invent a complete interview
