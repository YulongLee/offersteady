## Context

The desktop companion is now part of the live interview MVP path. It must collect the user's microphone, the interviewer's computer output, and selected screen captures, then publish status and artifacts to the backend so the web interview page can show live conversation and screenshot answers.

The current failure mode is severe because the UI can appear connected while the real capture path is not producing computer-output signal, screen capture preview/capture is not usable, and the user receives no clear notification when entering a live interview. Existing documentation already states that system output must be validated by real meter movement and backend frame receipts, not by a cosmetic green state.

Constraints:

- The project is still in prototype/MVP validation, so the solution must keep the original UI flow and remain simple.
- No service secrets may be stored in the desktop client.
- Diagnostics must avoid persisting raw audio, screenshots, transcripts, or personal material.
- Audio, ASR, screenshot, and backend adapters must remain replaceable.

## Goals / Non-Goals

**Goals:**

- Make microphone, computer output, and screen capture states evidence-based.
- Provide a deterministic notification/status transition when a desktop is bound to an interview and when the interview starts live capture.
- Add a full-chain diagnostic path that identifies whether failure is in capture, frame publish, backend receipt, ASR, transcript consumption, screen preview, or screenshot upload.
- Ensure local development release packages include the latest capture fixes and can be used for manual end-to-end testing.

**Non-Goals:**

- No hidden recording, bypass of platform permissions, or stealth behavior.
- No production signing/notarization work in this change.
- No Windows system-audio implementation in this change.
- No long-term persistence of raw audio or screenshots for diagnostics.

## Decisions

1. Evidence-based state over optimistic UI state.

   The companion will only show computer output as active when a real audio source reports signal or produced frames. The backend runtime will be treated as the source of truth for published frame receipts and transcript counts. If local signal is absent, backend frame count is zero, or a capture adapter is unavailable, the UI must show a clear waiting/error/unsupported state.

   Alternative considered: keep current status labels and only adjust thresholds. Rejected because lower thresholds can mask the real issue and still fail for Electron/macOS loopback or permission failures.

2. Adapter boundary for macOS computer output.

   Keep the current Electron capture path behind `SystemAudioAdapter`, but add self-test evidence and fallback/error semantics. If Electron loopback cannot produce signal on the current macOS environment, the implementation should be structured so a ScreenCaptureKit native adapter can replace the internals without changing the backend protocol.

   Alternative considered: immediately rewrite all computer-output capture with a native helper. Deferred because this proposal should first make the failure observable and keep MVP implementation scope manageable.

3. Screen capture must validate preview and upload separately.

   Screen capture readiness will require a visible preview or a successful capture result, not only a selected display id. Screenshot-answer requests will report failure with a concrete reason when preview/capture/upload fails.

   Alternative considered: treat `desktopCapturer.getSources()` as ready. Rejected because a source list can exist while real capture permissions or thumbnails fail.

4. Interview-entry notification is a first-class runtime event.

   When a binding transitions from registered/ready to bound/live, the desktop companion and web page should surface a stable notification/status message. This notification must not flicker during polling and must not expose backend URLs in user-facing connection copy.

   Alternative considered: rely on the existing connection card text. Rejected because the user currently cannot tell whether the session entered live capture or is merely registered.

5. Self-test uses synthetic, non-sensitive fixtures.

   The diagnostic path should generate local synthetic audio and screenshot/capture probes where possible, then verify backend runtime receipts and transcript flow. The report may store counters, timings, request ids, and error codes only.

   Alternative considered: manual-only verification. Rejected because this chain has multiple async boundaries and has already regressed repeatedly.

## Risks / Trade-offs

- Electron/macOS computer output may not capture some apps or system versions → show a truthful unsupported/error state and keep the adapter replaceable for ScreenCaptureKit.
- Increasing ASR final wait improves correctness but hurts realtime latency → use this only for proof of correctness; later optimize with partial transcript streaming.
- Native screen/audio helpers increase packaging complexity → keep helper health checks and release build verification explicit.
- Diagnostics can create false confidence if they only test synthetic sources → include both synthetic backend probes and real local playback/manual checks in acceptance.
- Polling can still cause UI flicker if multiple effects update the same copy → centralize connection copy and only allow live/error transitions to override stable waiting text.

## Migration Plan

1. Implement diagnostics and UI state changes behind existing desktop companion flows.
2. Rebuild the macOS local release package.
3. Run backend synthetic PCM probe and desktop packaged-app manual checks.
4. Update docs with the exact runbook and known limitations.
5. If the Electron computer-output adapter still cannot capture real local playback, record that result and implement or schedule the ScreenCaptureKit adapter as the next targeted change.
