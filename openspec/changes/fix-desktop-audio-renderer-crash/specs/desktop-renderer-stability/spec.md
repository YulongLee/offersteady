## ADDED Requirements

### Requirement: Bounded realtime audio worklet transfer
The desktop companion SHALL aggregate audio render quanta into bounded 1,024-sample batches before transferring them from an AudioWorklet to the renderer, and SHALL continue forwarding both microphone and system audio without waiting for an utterance endpoint.

#### Scenario: Continuous dual-channel interview capture
- **WHEN** microphone and system audio are captured continuously during a live interview
- **THEN** each channel transfers approximately one batch per 1,024 input samples rather than one transfer per 128-sample render quantum
- **AND** audio remains continuously eligible for realtime segmentation and upload

#### Scenario: Capture processor stops
- **WHEN** a capture processor is detached or its audio context is closed
- **THEN** the renderer SHALL remove message handlers and release the associated media, audio nodes, timers, and context

### Requirement: Display health updates do not run at audio callback frequency
The desktop companion MUST keep audio processing independent of React-facing health and meter updates and SHALL emit display health at a bounded cadence of no more than 10 updates per second per publisher.

#### Scenario: High-frequency audio input
- **WHEN** audio callbacks arrive faster than the display-health cadence
- **THEN** all audio batches SHALL remain available to the realtime pipeline while redundant display-only updates are suppressed

### Requirement: Unexpected renderer exits recover without a black window
The Electron main process SHALL detect an unexpected renderer exit and recreate the companion window unless the application is quitting, with bounded retry behavior.

#### Scenario: Renderer crashes during an interview
- **WHEN** Electron reports `render-process-gone` for the companion renderer with a non-clean reason
- **THEN** the unusable window SHALL be replaced with a newly loaded companion window
- **AND** reopening the application SHALL not show the dead renderer as a permanent black surface

#### Scenario: Repeated startup crashes
- **WHEN** renderer recovery exceeds the configured retry limit within the recovery window
- **THEN** the main process SHALL stop recreating windows and log the terminal recovery condition instead of entering an infinite loop

### Requirement: Production macOS release remains verifiable
The fixed companion SHALL be released as version 0.1.20 for arm64 and x64 using the existing bundle identifier and Developer ID production release flow.

#### Scenario: Release artifacts are produced
- **WHEN** the macOS production release workflow completes for an architecture
- **THEN** its final DMG SHALL pass strict code-sign verification, Gatekeeper assessment, and stapler validation before it is considered publishable

### Requirement: Renderer resource diagnostics are bounded and trendable
The companion SHALL record bounded counters for AudioWorklet callbacks, cross-thread messages, audio bytes, allocations, renderer memory, CPU and React renders without retaining PCM or transcript content.

#### Scenario: Sustained capture diagnostics
- **WHEN** capture remains active for 60 minutes
- **THEN** diagnostic snapshots SHALL be available at 0, 5, 10, 20, 30 and 60 minutes
- **AND** collecting diagnostics SHALL NOT update React state or cross the worklet boundary at audio callback frequency
- **AND** renderer RSS, heap, external memory and ArrayBuffer memory SHALL NOT show sustained linear growth

### Requirement: Renderer crash recovery restores realtime audio
The main process SHALL recreate a crashed renderer and the new renderer SHALL restore the current live interview's capture sources, AudioWorklet, realtime publisher and WebSocket from authoritative binding metadata.

#### Scenario: Renderer crashes during a live interview
- **WHEN** `render-process-gone` occurs while an interview is live
- **THEN** the main process SHALL record reason, exit code, memory summary and session-safe recovery metadata
- **AND** it SHALL destroy the unusable WebContents and create a new renderer
- **AND** the new renderer SHALL recreate microphone/system capture, worklets and publisher transport
- **AND** recovery SHALL be considered successful only after a fresh audio frame is produced and acknowledged

### Requirement: Capture health reflects evidence instead of intent
The companion SHALL model local realtime health as `STARTING`, `HEALTHY`, `DEGRADED`, `LOST` or `RECOVERING` and SHALL not report healthy capture solely because the interview command is live.

#### Scenario: Capture callback stops
- **WHEN** a source is expected to capture and its raw capture callback has not advanced for more than two seconds
- **THEN** the source SHALL enter `LOST`
- **AND** the user-facing state SHALL stop claiming normal capture
- **AND** bounded automatic source recovery SHALL start

#### Scenario: Published frame is not acknowledged
- **WHEN** the WebSocket is active and a pending or recently sent frame has not been acknowledged for more than three seconds
- **THEN** delivery SHALL enter `DEGRADED` or `LOST`
- **AND** bounded publisher/transport recovery SHALL start

#### Scenario: Source is silent but callbacks continue
- **WHEN** the audio source is silent and raw AudioWorklet callbacks continue at the expected cadence
- **THEN** the source SHALL remain healthy without unnecessary recovery

### Requirement: Reliability soak gates release
The companion SHALL pass real-device system-only, microphone-only and dual-channel 60-minute soak tests before this reliability change is considered release-ready.

#### Scenario: Sixty-minute soak completes
- **WHEN** each required soak reaches 60 minutes
- **THEN** renderer crashes, unexpected restarts, audio gaps over two seconds, dead publishers and zombie capture states SHALL each equal zero
- **AND** renderer RSS, heap and ArrayBuffer memory SHALL remain bounded
- **AND** a 120-minute soak MAY begin only after all three 60-minute soaks pass

### Requirement: Realtime transport amplification is observable without behavior changes
The companion SHALL expose local, bounded, per-channel counters at the AudioWorklet, publisher input, unique sequence, WebSocket write, ACK, sequence-gap, reconnect and buffer boundaries without changing transport behavior or persisting audio.

#### Scenario: Ten-second transport diagnostic interval completes
- **WHEN** a live microphone or system-audio capture interval reaches ten seconds
- **THEN** the companion SHALL log capture and publisher input rates, unique and actual WebSocket send rates, audio and total bytes, ACK and resend rates, gap and duplicate counts, buffer depths and send/byte amplification ratios for that channel
- **AND** a ratio over 1.2 SHALL be marked abnormal and a ratio over 2 SHALL be marked severe
- **AND** collection SHALL NOT enqueue, send, retry, acknowledge, drop, reconnect, or alter an audio frame

#### Scenario: A sequence is sent more than once
- **WHEN** the same channel and sequence crosses the actual WebSocket write boundary repeatedly
- **THEN** the companion SHALL count every write after the first as a resend and duplicate-sequence send
- **AND** it SHALL retain a bounded sample containing the maximum send count for diagnosis

### Requirement: Realtime transport recovery remains ordered and bounded
The desktop companion SHALL keep unacknowledged realtime audio writes bounded per logical channel and SHALL recover sequence gaps without replaying an entire pending queue.

#### Scenario: Server requests a recoverable missing sequence
- **WHEN** the Backend reports `sequence-gap` with an expected sequence that remains in the local buffer
- **THEN** the desktop SHALL pause later writes for that channel and resend only the expected frame
- **AND** it SHALL resume the bounded ordered window only after an authoritative acknowledgement advances the cursor

#### Scenario: Server repeats the same gap response
- **WHEN** identical gap responses arrive while the requested frame is already awaiting acknowledgement
- **THEN** the desktop SHALL suppress immediate duplicate resends
- **AND** actual WebSocket writes SHALL remain within the configured retry budget

#### Scenario: Expected sequence is no longer recoverable
- **WHEN** the Backend requests a sequence that is absent from the bounded local buffer
- **THEN** the desktop SHALL stop the stale transport, discard the explicitly unrecoverable pending interval, create a fresh publisher and reset sequencing before accepting new live audio
- **AND** the user-facing state SHALL remain recovering until a fresh frame is acknowledged

#### Scenario: Publisher connection supplies resume offsets
- **WHEN** a WebSocket connection reports per-channel `resumeOffsets`
- **THEN** the desktop SHALL prune already accepted frames and align its next ordered send with the server cursor before flushing pending audio

### Requirement: Transport amplification fails closed
The desktop and Backend SHALL bound the resource impact of repeated gaps, reconnects or acknowledgements that do not advance.

#### Scenario: Client amplification exceeds the commercial safety budget
- **WHEN** repeated sends or identical gap recovery attempts exceed the configured bound
- **THEN** the desktop SHALL close the affected transport and start bounded fresh-publisher recovery
- **AND** it SHALL not continue a resend storm in the background

#### Scenario: Defective publisher floods sequence gaps
- **WHEN** one Backend connection exceeds the bounded sequence-gap response budget without forward progress
- **THEN** the Backend SHALL close that connection with a retryable policy reason
- **AND** other interview sessions SHALL remain isolated from its resource usage

### Requirement: Commercial capture health requires delivery evidence
The companion SHALL not report normal capture while produced frames remain unacknowledged or while a publisher reset is in progress.

#### Scenario: Capture continues but ACK progress stops
- **WHEN** AudioWorklet callbacks continue but a sent frame receives no acknowledgement within the delivery deadline
- **THEN** the companion SHALL show degraded, lost or recovering state instead of `capturing`
- **AND** bounded transport recovery SHALL begin

### Requirement: Diagnostic telemetry cannot starve realtime audio
Browser performance acknowledgements SHALL use bounded concurrency and bounded pending storage, and Backend processing of those acknowledgements SHALL not block the realtime WebSocket event loop.

#### Scenario: Transcript updates produce a telemetry burst
- **WHEN** many transcript delivery or render measurements are produced faster than the Backend can accept them
- **THEN** the Web client SHALL keep at most one performance acknowledgement request in flight and a bounded pending queue
- **AND** excess diagnostic measurements MAY be dropped without affecting audio, transcript or answer delivery
- **AND** realtime frame acknowledgements SHALL remain independently serviceable

### Requirement: Commercial transport fix is released as a verified patch
The corrected companion SHALL use version 1.1.1 and SHALL retain bundle identifier `com.offersteady.companion` and realtime protocol version `2.0`.

#### Scenario: Production patch is published
- **WHEN** Backend protection and companion 1.1.1 pass their release gates
- **THEN** the Backend SHALL be deployed before the new desktop download manifest is made public
- **AND** macOS arm64 and x64 artifacts SHALL pass Developer ID, notarization, Gatekeeper and stapler verification
- **AND** the public release manifest SHALL expose version 1.1.1 with matching SHA-256 values
