## 1. Current-State Audit

- [x] 1.1 Trace the desktop launch, machine-code registration, polling and backend API base URL path; record where the companion can diverge from the Web backend.
- [x] 1.2 Trace Web preparation binding and live session start calls; record the backend state transitions that should be visible to the companion.
- [x] 1.3 Trace microphone, system-output and screen capture adapters from device selection through frame/preview production.
- [x] 1.4 Trace realtime publisher token creation, WebSocket connection, frame send, backend receipt, ASR result and Web transcript consumption.
- [x] 1.5 Produce a failure matrix covering current user-observed issues: no input audio, no system audio, no screen preview and no Web-to-companion connection update.

## 2. Shared Runtime Contract

- [x] 2.1 Add shared protocol types for desktop runtime stages, source health stages, failure reason codes and diagnostic report fields.
- [x] 2.2 Add backend runtime aggregation for registered device, active binding, session status, publisher status, source health, recent frame counters and recent ASR/transcript status.
- [x] 2.3 Add backend tests for registered-only, bound-not-live, live-without-publisher, publishing and ASR-failed runtime states.
- [x] 2.4 Update the companion to consume backend runtime status as the connection source of truth.

## 3. Audio Capture Reliability

- [x] 3.1 Refactor microphone capture into a controller that validates selected device id, permission, live track, RMS/peak signal and PCM frame production.
- [x] 3.2 Refactor system-output capture into a dedicated controller that validates actual computer playback capture rather than treating a static option as success.
- [x] 3.3 Ensure the companion shows warning/unsupported states when system-output loopback cannot produce signal or frames.
- [x] 3.4 Ensure microphone and system-output publishers are created only when the bound session is live.
- [x] 3.5 Add per-source frame acknowledgements or backend counters so the companion can show that frames reached Realtime Speech.
- [x] 3.6 Add regression tests for source health transitions and frame publishing error handling.

## 4. Screen Capture Reliability

- [x] 4.1 Refactor screen capture into a controller that owns selected display id, permission state and preview stream.
- [x] 4.2 Ensure selecting a display updates the Electron display media handler and later screenshot source consistently.
- [x] 4.3 Mark screen capture ready only after at least one preview frame is produced.
- [x] 4.4 Add tests or manual validation hooks for missing permission, missing display and successful preview states.

## 5. Web Live Session Integration

- [x] 5.1 Ensure Web machine-code binding writes a backend binding that companion polling can read without manual registration.
- [x] 5.2 Ensure Web start-interview transition updates the session to live before the companion creates publishers.
- [x] 5.3 Ensure backend ASR transcript events are returned to Web live state with stable roles “面试官” and “我”.
- [x] 5.4 Ensure quick answer can use the latest final interviewer transcript when manual input is empty.
- [x] 5.5 Preserve the approved Web prototype layout and avoid adding new product UI structure.

## 6. Diagnostics and Verification

- [x] 6.1 Add a local diagnostic command or report artifact that checks backend reachability, registration, binding, live session, publisher, audio source, screen source, ASR and Web transcript stages.
- [x] 6.2 Run backend realtime tests and add regressions for the new runtime status contract.
- [x] 6.3 Run desktop typecheck/unit tests for capture controllers and runtime status handling.
- [x] 6.4 Run Web tests or focused integration checks for binding, live transcript rendering and quick-answer transcript fallback.
- [ ] 6.5 Package the macOS arm64 companion and perform a local manual E2E: open companion, bind machine code in Web, start interview, speak into mic, play computer audio, verify transcripts appear in Web.
- [x] 6.6 Update `docs/desktop-distribution.md` or local run docs with the verified development workflow and known macOS system-output limitations.
