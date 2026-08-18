## ADDED Requirements

### Requirement: Partial transcripts remain visibly current
The live interview page SHALL display the latest received partial transcript without a fixed per-character animation backlog, and SHALL display a final transcript immediately when received.

#### Scenario: Long partial revision arrives
- **WHEN** the browser receives a partial transcript revision containing 100 Chinese characters
- **THEN** the visible transcript catches up within 250 ms under an active animation frame loop

#### Scenario: Final revision arrives while animation is behind
- **WHEN** a final transcript revision replaces an active partial
- **THEN** the page displays the complete final text on the next render without waiting for the partial animation backlog

### Requirement: Automatic answers stream without blocking audio processing
The backend SHALL start an automatically confirmed interviewer answer outside the realtime audio source worker and SHALL expose ordered answer progress before the provider completes the full response.

#### Scenario: High-confidence interviewer question is finalized
- **WHEN** system-audio ASR publishes a final high-confidence question
- **THEN** the transcript and confirmed question become available without waiting for complete answer generation
- **AND** the automatic answer task publishes its first visible chunk incrementally

#### Scenario: More audio arrives while an answer is generating
- **WHEN** a new audio frame arrives for the same session while an automatic answer is streaming
- **THEN** the realtime ingest worker accepts and processes the frame without waiting for the answer provider to finish

### Requirement: Existing automatic answer behavior is preserved
The streamed automatic path MUST retain the existing automatic prompt strategy, selected material context, answer history, points or pass settlement, cancellation semantics, and one-answer-per-candidate idempotency.

#### Scenario: Automatic answer completes successfully
- **WHEN** all provider chunks complete normally
- **THEN** the persisted task, final answer, usage record, session history, and billing settlement match the existing automatic answer behavior

#### Scenario: Provider fails after partial output
- **WHEN** the provider fails after one or more visible chunks
- **THEN** the task reaches a recoverable failed state, preserves safe partial text, and releases reserved billing according to existing rules

#### Scenario: Realtime session reconnects during generation
- **WHEN** the browser reconnects while an automatic answer is streaming
- **THEN** replayed progress reconciles by task identity without duplicate answers or duplicate billing

### Requirement: Speech endpointing uses bounded low-latency silence windows
The desktop companion SHALL finalize system-audio speech after 500 ms of continuous silence and microphone speech after 700 ms while preserving existing pre-speech buffering, adjacent-turn assembly, and duplicate suppression.

#### Scenario: Interviewer stops speaking
- **WHEN** system audio remains below the continuation threshold for 500 ms
- **THEN** the companion emits one final frame for the active segment

#### Scenario: Candidate stops speaking
- **WHEN** microphone audio remains below the continuation threshold for 700 ms
- **THEN** the companion emits one final frame for the active segment

### Requirement: Latency is observable and regression tested
The system SHALL provide automated evidence for capture segmentation, transcript publication, frontend catch-up, automatic answer first chunk, terminal completion, cancellation, and non-blocking audio processing without storing raw user audio.

#### Scenario: Synthetic end-to-end performance validation
- **WHEN** the latency test uses synthetic interview audio and the configured providers
- **THEN** the report separates silence wait, ASR finalization, session publication, visible transcript catch-up, answer first chunk, and answer completion timings

### Requirement: Idle realtime streams avoid database polling churn
Realtime event cursors SHALL remain responsive without validating the database-backed session lease on every cursor poll.

#### Scenario: Connected stream has no new event
- **WHEN** a live page remains connected without new transcript or answer events
- **THEN** Redis-backed cursor checks MAY continue at the existing cadence
- **AND** database-backed session/lease validation SHALL run no more than once every two seconds per stream
- **AND** a replaced session SHALL receive a revocation event after the next bounded validation
