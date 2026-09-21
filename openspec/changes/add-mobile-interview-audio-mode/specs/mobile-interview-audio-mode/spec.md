## ADDED Requirements

### Requirement: Session-level interview audio mode
The system SHALL persist an interview audio mode of `computer` or `mobile` for every realtime interview session, SHALL default existing and unspecified sessions to `computer`, and MUST reject changes after the session leaves preparation.

#### Scenario: Existing flow keeps computer mode
- **WHEN** a realtime interview session is created without an audio mode
- **THEN** the system stores `computer` and preserves the existing microphone plus system-audio behavior

#### Scenario: Mobile mode is locked after start
- **WHEN** a user tries to change a mobile or computer audio mode after the interview has started
- **THEN** the system rejects the change without altering the running audio topology

### Requirement: Mobile mode uses the Mac microphone only
The Desktop companion SHALL publish only the Mac microphone for a mobile interview and SHALL NOT require, start, or publish computer system audio for that session.

#### Scenario: Mobile interview starts without system audio
- **WHEN** the session is configured for mobile mode and the Mac microphone check succeeds
- **THEN** the companion can start the realtime publisher without a usable system-audio source

#### Scenario: Unexpected system audio is ignored
- **WHEN** system-audio frames reach the Backend for a mobile-mode session
- **THEN** the Backend excludes those frames from transcription, question detection, and answer generation

### Requirement: Computer mode remains dual-channel
The system MUST preserve the existing computer interview routing in which Mac microphone audio represents the candidate and computer system audio represents the interviewer.

#### Scenario: Computer interview regression
- **WHEN** a computer-mode realtime interview starts
- **THEN** the companion publishes microphone and system audio and the Backend retains their existing role mapping

### Requirement: Mobile microphone can drive the answer chain
For a mobile-mode interview, the system SHALL allow eligible final Mac-microphone transcripts to enter question confirmation, manual quick-answer, and enabled automatic-answer flows while retaining question completeness, stability, and duplicate-suppression safeguards.

#### Scenario: Final phone question is confirmed
- **WHEN** a final Mac-microphone transcript in mobile mode satisfies the configured question eligibility checks
- **THEN** the system can confirm it as the active question and make it available to the existing answer generation pipeline

#### Scenario: Partial or repeated speech is not answered
- **WHEN** a mobile microphone transcript is partial, empty, unstable, or a suppressed duplicate
- **THEN** the system does not create a new answer generation request from that transcript

#### Scenario: Automatic answering remains opt-in
- **WHEN** a mobile question is confirmed but automatic answering is disabled
- **THEN** the system does not generate an automatic answer and still permits the user to request a manual quick answer

### Requirement: Honest mixed-audio presentation
The Web application SHALL label mobile-mode microphone transcript content as “现场声音” in Chinese UI or the equivalent localized phrase and MUST NOT claim reliable separation between interviewer and candidate speech.

#### Scenario: Mobile transcript is displayed
- **WHEN** a mobile-mode microphone transcript appears in the live workspace
- **THEN** the transcript uses the mixed onsite-audio label and the answer remains identified as AI-generated guidance

### Requirement: Mobile audio preparation guidance
The preparation experience SHALL explain that the phone must use speakerphone near the Mac, headphones prevent the Mac from hearing the interviewer, and ambient noise can reduce recognition quality. It SHALL require a usable Mac microphone signal before start.

#### Scenario: Microphone is unavailable
- **WHEN** mobile mode is selected and the Mac microphone permission or signal check fails
- **THEN** the system blocks start and shows a recovery action without requesting system-audio capture

### Requirement: Mobile mode preserves privacy and cleanup
The system MUST NOT introduce raw-audio persistence for mobile interviews and SHALL release mobile-mode publisher, stream, and mode-cache resources on the same end, cancel, expiry, and disconnect paths as computer interviews.

#### Scenario: Mobile interview ends
- **WHEN** a mobile-mode interview reaches a terminal state
- **THEN** its realtime audio resources and mode-specific cached state are removed without retaining raw audio
