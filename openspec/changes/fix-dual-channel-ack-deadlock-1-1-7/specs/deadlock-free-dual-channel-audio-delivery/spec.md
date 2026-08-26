## ADDED Requirements

### Requirement: Channel delivery health is independent
The companion SHALL track media production, send progress, acknowledgement progress, pending age, and recovery state independently for microphone and system audio on the shared transport.

#### Scenario: One replacement channel is acknowledged
- **WHEN** system audio receives a fresh acknowledgement after transport replacement while a produced microphone frame remains unacknowledged
- **THEN** the companion SHALL mark only system audio healthy and SHALL keep the microphone acknowledgement deadline active

#### Scenario: Recovered channel remains silent
- **WHEN** a replacement channel produces no media after receiving authoritative resume offsets
- **THEN** the companion SHALL keep that channel ready and idle without consuming an acknowledgement timeout or falsely reporting delivered media

### Requirement: A saturated send window cannot remain deadlocked
The companion SHALL initiate one bounded shared-transport recovery when any active channel has a full in-flight window and no forward acknowledgement progress beyond the configured deadline.

#### Scenario: Capture continues after acknowledgements stop
- **WHEN** capture callbacks and produced frames continue but the channel acknowledgement high-water mark does not advance and eight frames remain in flight
- **THEN** the companion SHALL replace the transport through the single-flight recovery path instead of allowing the queue to grow indefinitely

#### Scenario: Continuous sends do not postpone detection
- **WHEN** new frames continue to enter a channel whose oldest frame remains unacknowledged
- **THEN** later send timestamps SHALL NOT reset the oldest-unacknowledged deadline

### Requirement: Unexpected WebSocket closure always recovers
The companion SHALL suppress reconnect only for a closure explicitly initiated by stopping or replacing that exact transport generation.

#### Scenario: Remote endpoint closes with code 1000
- **WHEN** the active socket closes with code 1000 without an intentional local stop
- **THEN** the companion SHALL enter reconnect or bounded replacement recovery and SHALL NOT leave capture running against a null socket

#### Scenario: Stale socket closes after replacement
- **WHEN** an old socket emits a delayed close or acknowledgement after a newer generation is active
- **THEN** the companion SHALL ignore the stale event and preserve the current transport and channel health

### Requirement: Publisher replacement reconciles sequence state atomically
The companion SHALL pause media writers, obtain authoritative resume offsets, align each channel sequencer, retire stale in-flight state, and resume capture without a non-contiguous replay.

#### Scenario: Replacement publisher starts from zero
- **WHEN** the backend returns a resume offset of -1 for a replacement publisher
- **THEN** the companion SHALL start that channel at sequence 0 and SHALL discard envelopes owned by the retired publisher generation

#### Scenario: Replacement publisher resumes an existing offset
- **WHEN** the backend returns a non-negative channel offset
- **THEN** the companion SHALL send only contiguous frames beginning at offset plus one and SHALL never resend frames at or below the offset

#### Scenario: Replacement token preserves the session boundary
- **WHEN** a replacement publisher token connects for the same interview session after its predecessor delivered channel frames
- **THEN** the backend SHALL return the highest accepted offset for each logical session channel regardless of which publisher token delivered it

### Requirement: Recovery failure is visible and bounded
The companion SHALL stop claiming healthy delivery when bounded recovery is exhausted and SHALL provide an explicit reconnect action while leaving unaffected local state safe.

#### Scenario: A channel never acknowledges replacement media
- **WHEN** all configured replacement attempts expire after that channel produces media
- **THEN** the companion SHALL mark delivery lost, clear bounded PCM buffers, stop upload, and display a reconnect-required error

### Requirement: Release 1.1.7 is commercially verifiable
The release SHALL provide reproducible regression, soak, packaging, and metadata-only production evidence without retaining interview content or credentials.

#### Scenario: Production-shaped dual-channel regression runs
- **WHEN** tests reproduce a healthy start, one-channel replacement ACK, other-channel stall, full windows, and unexpected clean close
- **THEN** both channels SHALL either resume acknowledged forward progress within the bounded recovery budget or surface a truthful terminal failure

#### Scenario: Companion artifacts are published
- **WHEN** version 1.1.7 is promoted
- **THEN** macOS arm64, macOS x64, and Windows x64 release metadata SHALL identify version 1.1.7 with immutable checksums and required signing status
