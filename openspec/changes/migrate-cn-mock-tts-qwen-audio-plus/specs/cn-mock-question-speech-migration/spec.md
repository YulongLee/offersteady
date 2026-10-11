## ADDED Requirements

### Requirement: CN dedicated question speech replacement
CN mock interviews SHALL synthesize validated existing questions with `qwen-audio-3.0-tts-plus`, supported female voice `longanhuan_v3.6`, and the inference WebSocket endpoint. This replaces the CN model-specific speech requirement in the existing add-ai-mock-interview change. Output MUST remain incremental 24 kHz mono PCM compatible with the current browser. TTS MUST NOT generate or modify interview questions. Provider credentials MUST remain server-side.

#### Scenario: Existing question is spoken
- **WHEN** a validated CN mock question is published
- **THEN** run-task starts one TTS task, continue-task sends the same text only after matching task-started, finish-task closes input, and binary PCM streams to the existing browser protocol without an assistant update

### Requirement: Bounded and recoverable synthesis
Both speech protocols MUST share existing text, audio, concurrency and timeout limits. New inference events MUST have valid shape and matching task identity; audio before start, provider failure, incomplete PCM or completion without audio MUST fail safely. Audio MUST NOT be persisted or cached after the stream. Ending, replaying or cancelling MUST close the socket and return capacity even after the first chunk was yielded.

#### Scenario: Stream fails
- **WHEN** the provider rejects, times out, returns malformed or mismatched events, exceeds limits or disconnects before completion
- **THEN** the adapter emits a redacted speech error, closes resources and leaves the existing text-continuation/retry path available without a new question or fee

#### Scenario: End or replay during speech
- **WHEN** consumption is cancelled while waiting or after an audio chunk
- **THEN** socket and generator close, capacity returns to its prior bound and a later independent replay uses a new task ID

### Requirement: Existing features remain isolated
The migration MUST NOT change ordinary quick/detailed answers, screenshot handling, mock question/report generation, ASR, microphone capture windows, billing, desktop protocol or Global production configuration. Legacy realtime TTS MUST remain usable for configurations that still select it. Regression checks MUST exercise the existing runtime speech failure/cancellation paths.

#### Scenario: Ordinary or legacy flow
- **WHEN** an ordinary interview runs or a legacy TTS configuration is selected
- **THEN** its existing routing and protocol remain unchanged, and no new model is automatically selected for Global

### Requirement: Verified baseline and idle-gated CN rollout
The release MUST derive from the actual current CN backend image, changing only the TTS adapter patch and three explicit TTS environment settings. Unit tests and real-provider checks through the candidate adapter MUST pass before an idle-gated backend-only cutover. Other containers and runtime settings MUST be unchanged; health failure MUST restore the original backend configuration. Synthetic provider checks MUST NOT create interview records, debit product points or store audio. Real-device acceptance MUST be reported separately.

#### Scenario: Safe cutover
- **WHEN** candidate checks pass and ordinary/mock interviews, active pages/audio, answer and material tasks are idle
- **THEN** only the CN backend is switched and health, effective TTS settings and unchanged non-targets are verified

#### Scenario: Online interview exists
- **WHEN** any protected user work is active before cutover
- **THEN** deployment is deferred without terminating or changing that work
