## ADDED Requirements

### Requirement: Committing turns remain bounded
The backend SHALL retain source-turn supervision after terminal admission until provider finalization or an explicit incomplete terminal state.

#### Scenario: Provider completion is missing
- **WHEN** a terminal frame is admitted but the provider does not complete within the source deadline
- **THEN** the backend publishes one monotonic incomplete terminal state, clears the busy presentation, and recreates only the affected source

#### Scenario: Provider completion succeeds
- **WHEN** the provider completes within the deadline
- **THEN** the matching segment becomes provider-final and its temporary recovery state is released

### Requirement: Provider recovery uses a complete ephemeral utterance
The backend SHALL keep a bounded in-memory PCM buffer for only the active source segment and SHALL use it for at most one provider retry after connection failure.

#### Scenario: Source connection fails before final completion
- **WHEN** complete buffered PCM remains available for the segment
- **THEN** the retry sends the complete ordered utterance rather than only the final frame payload

#### Scenario: Complete PCM is unavailable
- **WHEN** a safe complete replay cannot be constructed
- **THEN** the backend does not perform a partial-audio retry and terminalizes the latest stable transcript as incomplete

#### Scenario: Segment reaches a terminal state
- **WHEN** a segment becomes final or incomplete, or its session pauses, ends, or retires
- **THEN** its buffered PCM is removed from memory and is never persisted or emitted in diagnostics

### Requirement: New audio is not lost behind provider completion
The source worker SHALL preserve bounded ordering for subsequent frames while an earlier segment is committing and SHALL prioritize terminal intent over superseded partial presentation work.

#### Scenario: A new utterance begins during slow completion
- **WHEN** the prior segment is still committing and frames for a new segment arrive
- **THEN** the new audio is admitted within bounded capacity and is processed after the prior segment terminalizes without being mistaken for the prior utterance

### Requirement: Terminal and first-visible SLOs are verifiable
The release SHALL record content-free timing stages and SHALL target speech-end-to-terminal P95 at or below 1.5 seconds, P99 at or below three seconds, and no unlabelled transcribing state beyond four seconds.

#### Scenario: Local acceptance run completes
- **WHEN** synthetic or user-authorized microphone and system-audio fixtures are exercised
- **THEN** the report contains per-source latency distributions, missing-terminal counts, retry outcomes, and queue bounds without raw audio or transcript text
