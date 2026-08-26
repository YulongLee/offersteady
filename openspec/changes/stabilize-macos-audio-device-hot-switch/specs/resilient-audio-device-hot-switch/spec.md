## ADDED Requirements

### Requirement: Audio route changes preserve the live publisher
The desktop companion SHALL reconcile operating-system audio-device changes without recreating the shared live publisher when only an input or output route changes.

#### Scenario: Selected headset remains available
- **WHEN** macOS emits one or more device-change notifications and the selected microphone remains available
- **THEN** the companion SHALL retain the selection and SHALL NOT recreate the publisher or healthy system-audio source

#### Scenario: Selected headset is removed
- **WHEN** the selected microphone disappears during a live interview
- **THEN** the companion SHALL switch only the microphone source to an available default route while keeping the WebSocket and system-audio channel active

#### Scenario: No replacement microphone is available
- **WHEN** the selected microphone disappears and macOS exposes no usable replacement
- **THEN** the companion SHALL mark only the microphone unavailable and SHALL keep system-audio capture and the live session active

### Requirement: Source switching is serialized and monotonic
The desktop companion SHALL serialize source transitions, converge on the latest requested device, and preserve the active publisher's channel sequence and terminal ordering.

#### Scenario: Repeated device notifications arrive during recovery
- **WHEN** a second microphone selection change arrives while the first source switch is still running
- **THEN** the companion SHALL finish or cancel safely and converge on the latest available selection without overlapping active microphone runtimes

#### Scenario: An utterance is active during a route change
- **WHEN** the old microphone route ends while a segment is active
- **THEN** the companion SHALL emit at most one terminal boundary before starting the replacement source and SHALL continue with a strictly increasing microphone sequence

### Requirement: Gap recovery cannot amplify traffic without bound
The desktop transport SHALL apply retry cooldown and retry budget checks before mutating in-flight state so duplicate gap responses cannot create a resend storm.

#### Scenario: Duplicate gap responses arrive inside cooldown
- **WHEN** the server repeatedly reports the same expected sequence inside the configured cooldown window
- **THEN** the desktop SHALL perform no additional resend and SHALL preserve the existing in-flight markers

#### Scenario: Gap retry budget is exhausted
- **WHEN** the same expected sequence exceeds its bounded resend budget
- **THEN** the desktop SHALL replace the transport once through the bounded recovery path instead of continuing duplicate sends

### Requirement: Silent recovery does not consume replacement attempts
The desktop companion SHALL distinguish a control-plane-ready silent source from an unacknowledged media frame.

#### Scenario: Replacement source remains silent
- **WHEN** a replacement publisher receives valid resume offsets but neither channel produces speech
- **THEN** the companion SHALL keep the publisher ready without starting a media acknowledgement timeout or consuming another replacement attempt

#### Scenario: Replacement source produces a frame
- **WHEN** a recovered source produces its first frame
- **THEN** the companion SHALL require a bounded acknowledgement and SHALL return to capturing after the frame is accepted

### Requirement: Commercial hot-switch release is verifiable
The release SHALL increment the companion patch version and verify device switching with metadata-only evidence that excludes PCM, transcript content, and credentials.

#### Scenario: Version 1.1.6 artifacts are published
- **WHEN** the hot-switch fix is promoted
- **THEN** macOS arm64, macOS x64, and Windows x64 release metadata SHALL identify version 1.1.6 with immutable checksums

#### Scenario: Production acceptance is performed
- **WHEN** a user removes or reconnects a headset during a live session
- **THEN** verification SHALL record only connection, channel, sequence, acknowledgement, retry, and latency metadata
