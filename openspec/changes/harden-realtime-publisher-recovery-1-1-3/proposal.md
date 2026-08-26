## Why

Production system-audio testing on desktop 1.1.2 reproduced a false-online failure: local capture continued after audio acknowledgements stopped, three replacement publishers failed to prove forward progress, and the advertised HTTP fallback returned 422 before reaching a production-disabled legacy route. Users consequently saw delayed or frozen subtitles while the product still appeared to be capturing.

## What Changes

- Make replacement-publisher recovery distinguish an established transport from first-audio forward progress so silence cannot cause publisher churn, while keeping the UI recovering until a real frame is acknowledged.
- Remove the unusable legacy HTTP frame fallback from the production desktop path and fail visibly after bounded WebSocket recovery is exhausted.
- Make capture health follow produced-frame, send, ACK and buffer evidence; never report healthy capture when upload progress has stopped.
- Add a bounded minimal initial realtime snapshot so entering an interview does not wait for full retained event history.
- Preserve immediate partial transcript delivery and monotonic in-place revision rendering.
- Release the compatible desktop correction as patch version 1.1.3 without changing the bundle identifier or realtime protocol version 2.0.
- Add deterministic regressions for the observed ACK-269 stall, recovery during silence, exhausted recovery, false-online prevention, snapshot latency work isolation and partial delivery.
- Keep raw audio, transcripts and interview content out of diagnostics and test fixtures.

## Capabilities

### New Capabilities

- `commercial-realtime-recovery`: Defines bounded publisher recovery, evidence-backed capture health, truthful terminal failure, minimal stream bootstrap and verified desktop 1.1.3 release behavior.

### Modified Capabilities

None.

## Impact

- Desktop: realtime publisher recovery, transport readiness/ACK state, capture health, fallback behavior, diagnostics, package/release metadata and tests.
- Backend: compatible realtime connection readiness metadata and minimal stream bootstrap behavior; no key, billing, ASR model or transcript persistence changes.
- Web: live-session bootstrap and capture-health presentation regressions; no interview content or answer behavior changes.
- Deployment: compatible Backend/Web changes precede the signed desktop 1.1.3 artifact and public manifest update. Protocol 2.0 and existing clients remain supported.
