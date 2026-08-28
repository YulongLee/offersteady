## ADDED Requirements

### Requirement: Local speech admission rejects ambient noise without losing quiet speech
The companion SHALL admit a source turn using a bounded calibrated noise baseline, source-specific sustained activity and hysteresis, and SHALL retain a bounded pre-speech window. A single fixed RMS crossing or short transient MUST NOT be sufficient to publish a turn.

#### Scenario: Microphone remains in ambient noise
- **WHEN** the microphone receives steady room noise and short keyboard-like transients without sustained speech evidence
- **THEN** no audio turn is published and no transcript is created

#### Scenario: Quiet speech follows calibration
- **WHEN** sustained quiet speech is measurably above the calibrated source baseline
- **THEN** the source publishes its first frame within a bounded interval and includes the retained first syllables

#### Scenario: Steady low-level system output continues
- **WHEN** computer output contains stable low-level digital or program noise without speech-like variation
- **THEN** the source remains idle instead of repeatedly creating ASR turns

### Requirement: Preparation calibration continues safely into live mode
The companion SHALL transfer a fresh verified media source and content-free calibration evidence into live capture without transferring preparation PCM, reopening a healthy source, or resetting its calibrated baseline.

#### Scenario: Verified source becomes live
- **WHEN** a fresh preparation source passes transition validation and the interview becomes live
- **THEN** the live publisher promotes the same source with its bounded calibration metadata and begins publishing only post-live admitted audio

#### Scenario: Calibration is stale at transition
- **WHEN** a source is muted, ended, stalled, rerouted, or its readiness expires before live transition
- **THEN** only that source is reopened and recalibrated while the other healthy source continues

### Requirement: Preparation automatically warms the realtime path
After the companion is bound, preparation SHALL open and calibrate configured local sources and prewarm both provider channels without requiring test playback or prior real speech. It SHALL NOT publish, persist, upload, or transcribe preparation PCM. A successful start SHALL be observed by the bound companion within 500 milliseconds and SHALL promote healthy prepared sources without reopening them.

#### Scenario: Bound user remains silent in preparation
- **WHEN** the companion is online, required permissions are granted, callbacks are healthy, and the user has not played or spoken any sound
- **THEN** preparation continues automatically and the absence of prior real signal does not create a mandatory Web sound gate

#### Scenario: User starts a prepared interview
- **WHEN** the Backend commits the interview to `live`
- **THEN** the bound companion observes the control transition within 500 milliseconds even while its window is behind the interview browser, promotes the prepared sources, and publishes only post-live admitted audio

#### Scenario: Preparation lasts before start
- **WHEN** a bound user remains on preparation longer than the initial provider prewarm interval
- **THEN** provider readiness remains lifecycle-persistent or is idempotently refreshed without delaying the successful start response

### Requirement: First speech and terminal latency are bounded and observable
The system MUST expose privacy-safe stage timing from callback readiness through first frame/partial and from last meaningful speech through terminal ACK, provider completion or recovery, and browser presentation. It MUST NOT include raw PCM or transcript text in those diagnostics.

#### Scenario: Actual speech begins after live entry
- **WHEN** a verified source begins sustained speech after the live publisher is authorized
- **THEN** the first audio frame is sent within 400 milliseconds at P95 and the first visible partial is rendered within 1.5 seconds at P95 on the reference network

#### Scenario: Operator investigates a slow turn
- **WHEN** a turn exceeds a release gate
- **THEN** diagnostics identify the slow stage, source, segment-safe identifier, thresholds, timings, queue state, terminal reason, and recovery state without content payloads

### Requirement: Provider finalization cannot leave a visible turn active indefinitely
After desktop terminal admission, the Backend SHALL resolve the visible turn to authoritative `final` or explicit recoverable `incomplete` within three seconds, SHALL preserve the latest visible partial on timeout, and SHALL recover only the affected source.

#### Scenario: Provider completes after manual commit
- **WHEN** the provider returns authoritative completion within the finalization budget
- **THEN** the Backend publishes one monotonic final revision and the Web stops showing an active transcript

#### Scenario: Provider completion is missing
- **WHEN** provider completion does not arrive within the two-second budget
- **THEN** the Backend publishes the latest visible partial once as `incomplete`, closes only that provider source generation, and accepts later speech without retrying the same terminal operation

#### Scenario: Desktop terminal never arrives
- **WHEN** an active source stops producing frames beyond the 2.5-second watchdog boundary
- **THEN** the Backend emits one explicit incomplete recovery terminal and leaves the other source running

### Requirement: Companion 1.2.7 remains reversible and product-compatible
The release SHALL preserve the approved layout, transparent icon family, bundle identity, production endpoints, protocol compatibility, and privacy defaults, and SHALL retain independent rollback artifacts for Backend, Web, and the previously installed companion.

#### Scenario: Production rollout succeeds
- **WHEN** full verification passes and Backend then Web are deployed before the signed Apple Silicon companion is installed
- **THEN** health, compatibility, version, signing, endpoints, and rollback artifacts are verified before user acceptance begins

### Requirement: A live companion binding remains stable and reconnect state is truthful
The companion MUST remain pinned to its active live session until the Backend authoritatively releases that binding. Another account or session MUST NOT silently replace a device binding that is serving a live interview. The global `reconnecting` state MUST represent recovery after an established transport or source failure and MUST NOT be emitted merely because the initial publisher is opening or one source health record has not arrived yet.

#### Scenario: A newer binding appears while the current session is live
- **WHEN** the companion polls with its current session and binding identifiers and that binding remains active for the registered device generation
- **THEN** the Backend returns the pinned binding and the companion keeps its existing publisher without reopening audio sources

#### Scenario: Another account attempts to take over a live device
- **WHEN** a different account binds the same machine code while its existing device binding serves a live interview
- **THEN** the Backend rejects the request with an explicit conflict and leaves the active binding and publisher unchanged

#### Scenario: The pinned session is no longer active
- **WHEN** the pinned session ends, the binding becomes stale, the device generation changes, or the publisher receives an authoritative terminal session response
- **THEN** the companion releases the pin and resumes normal binding discovery without requiring an application restart

#### Scenario: Initial publisher startup is still in progress
- **WHEN** a live binding has been observed but the first transport or one source health record is still starting
- **THEN** the UI keeps the non-alarming live capture state and does not show an audio-gap reconnect warning

#### Scenario: An established transport enters recovery
- **WHEN** a previously healthy publisher loses its transport or an established source reports `reconnecting`
- **THEN** the companion and Web expose `reconnecting` until healthy capture is restored
