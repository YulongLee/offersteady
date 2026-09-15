## 1. Session lifecycle cleanup

- [x] 1.1 Add a single session-state cleanup helper for realtime service short-lived indexes and call it from `_reset_realtime_session`.
- [x] 1.2 Ensure ASR gateway close paths remove source sessions and expose closure diagnostics without retaining session objects.
- [x] 1.3 Add regression tests for explicit end, idle reclamation, repeated termination, and zero active provider sessions.

## 2. Screenshot transient data cleanup

- [x] 2.1 Add locked expiry sweeping for screenshot intents, pending payloads, and uploaded image bytes.
- [x] 2.2 Invoke the sweep on upload lifecycle boundaries and add an idempotent cleanup hook for completed or failed tasks.
- [x] 2.3 Add regression tests for abandoned uploads, expiry, and repeated release.

## 3. Verification and observability

- [x] 3.1 Extend realtime metrics with short-lived resource counts needed to verify cleanup without exposing image/audio contents.
- [x] 3.2 Run targeted backend tests and OpenSpec strict validation; record any environment limitations.
