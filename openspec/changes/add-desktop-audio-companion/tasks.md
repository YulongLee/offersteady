## 1. Platform and Protocol Decisions

- [x] 1.1 Select macOS 14.2+ as the first supported operating system based on available test hardware
- [x] 1.2 Decide whether the first release requires separate microphone and system-audio channels
- [x] 1.3 Select the desktop shell and document the trade-off between cross-platform and native audio access
- [x] 1.4 Define typed capability, permission, source, capture-state, audio-frame and device-status contracts
- [x] 1.5 Define compatibility rules between Web, server and desktop companion protocol versions
- [x] 1.6 Define the universal x64/arm64 macOS distribution decision

## 2. Web Download and Device Experience

- [x] 2.1 Build the Web download page with detected-platform recommendation and manual platform selection
- [x] 2.2 Add supported-version, installation-purpose, privacy and permission explanations
- [x] 2.3 Build the interview-workspace card for download, launch, bind, diagnose and revoke actions
- [x] 2.4 Display desktop-device online, permission, source, capture, reconnect and error states on desktop and mobile Web
- [x] 2.5 Add unsupported-platform and browser-input fallback paths
- [ ] 2.6 Add component and responsive tests for all download and device states

## 3. Desktop Companion Shell

- [x] 3.1 Scaffold the minimal desktop application with signed-development configuration and no business-content views
- [x] 3.2 Implement not-connected, permission-required, ready, capturing, paused, reconnecting and error state transitions
- [x] 3.3 Implement persistent visible capture status in the window and supported menu-bar or tray surface
- [x] 3.4 Implement explicit start, pause, resume, stop and disconnect controls
- [x] 3.5 Ensure application restart always returns to a non-capturing state
- [x] 3.6 Add unit tests for the capture state machine and forbidden hidden-start paths
- [x] 3.7 Configure universal macOS DMG/ZIP targets and required permission descriptions

## 4. Audio Permissions and Sources

- [x] 4.1 Implement the common audio-source adapter and runtime capability detection interface
- [ ] 4.2 Implement microphone permission request, device enumeration and source selection for the first platform
- [ ] 4.3 Implement system-audio permission and capture for the first supported platform
- [x] 4.4 Implement independent source identifiers, timestamps and sequence numbering for microphone and system audio
- [ ] 4.5 Build live level meters, silent-source detection and disconnected-device recovery
- [x] 4.6 Implement bounded in-memory audio buffering with no local recording-file writes
- [ ] 4.7 Add synthetic and virtual-device tests for permission denied, silence, disconnect and source switching

## 5. Session Binding and Authorization

- [x] 5.1 Implement server creation of short-lived one-time desktop binding tokens scoped to a user and interview session
- [ ] 5.2 Implement Web deep-link launch and manual code fallback
- [ ] 5.3 Implement desktop binding confirmation and exchange for a limited device credential
- [x] 5.4 Store the device credential using the supported operating-system secure credential facility
- [ ] 5.5 Implement Web-initiated device revocation and immediate connection termination
- [x] 5.6 Add security tests for expired, replayed, wrong-session and revoked credentials

## 6. Audio Transport and Recovery

- [ ] 6.1 Define a replaceable secure audio transport interface and select the MVP transport implementation
- [ ] 6.2 Implement authenticated connection establishment, heartbeat and device-status events
- [ ] 6.3 Implement compressed ordered audio-frame transmission for each active source
- [ ] 6.4 Implement server acknowledgements and duplicate-frame rejection
- [ ] 6.5 Implement reconnect and resend from the bounded in-memory buffer
- [ ] 6.6 Report an explicit audio gap when interruption exceeds buffer capacity
- [ ] 6.7 Add integration tests for ordering, duplication, network interruption, buffer overflow and revocation

## 7. Realtime Transcription Integration

- [ ] 7.1 Define the streaming-transcription adapter and normalized transcript-event contract
- [ ] 7.2 Implement one provider adapter without exposing provider details to the session bridge
- [ ] 7.3 Preserve source, time range, confirmation and uncertainty metadata on transcript events
- [ ] 7.4 Publish confirmed transcript events into the authoritative interview session
- [ ] 7.5 Prevent uncertain or incomplete transcripts from being presented as reliable questions
- [ ] 7.6 Add transcription eval fixtures for two speakers, overlap, silence, noise, reconnection and uncertain text

## 8. Privacy, Release and End-to-End Verification

- [ ] 8.1 Verify raw audio is not written to local files or retained by default after transient processing
- [ ] 8.2 Redact audio payloads, transcript content, credentials and binding tokens from logs
- [ ] 8.3 Add user-visible data-flow, third-party processing and stop/delete disclosures before capture
- [ ] 8.4 Configure installation-package signing and a verifiable download origin for the first platform
- [ ] 8.5 Implement version compatibility rejection and the approved upgrade path
- [ ] 8.6 Run an end-to-end test from Web download through binding, capture, transcript, Web synchronization, pause and revoke
- [ ] 8.7 Verify every scenario in both capability specs and document any deferred platform behavior
- [ ] 8.8 Update project documentation with supported platforms, permissions, privacy behavior and troubleshooting steps
