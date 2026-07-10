## 1. Baseline Diagnostics

- [x] 1.1 Add a single realtime E2E diagnostic command that accepts `sessionId`, `manualCode`, and `userId` and prints binding, publisher, frame receipt, ASR, web runtime, and screenshot stage results.
- [x] 1.2 Add a backend-only synthetic PCM probe assertion that reports ASR accepted, transcript status, provider timeout, and suppressed filler separately.
- [x] 1.3 Add a real desktop capture probe that requires non-zero local PCM frames before attempting ASR.
- [x] 1.4 Ensure diagnostic artifacts store only counters, timings, request ids, dimensions, and error codes, not raw audio or screenshot data.

## 2. macOS Native Audio Capture

- [x] 2.1 Extend the native macOS runtime to expose microphone PCM frames with timestamps, source id, level, and error codes.
- [x] 2.2 Extend the native macOS runtime to expose ScreenCaptureKit/system-output PCM frames with timestamps, source id, level, and error codes.
- [x] 2.3 Add Electron IPC bridge for native PCM frames without storing raw audio on disk.
- [x] 2.4 Make native capture the primary live publisher source and keep Electron WebAudio as fallback/local monitor only.
- [x] 2.5 Ensure microphone and system output start independently and one source failure does not stop the other.

## 3. Backend Runtime Evidence

- [x] 3.1 Update realtime runtime status to distinguish binding ready, publisher created, local signal observed, frame receipt received, ASR accepted, and transcript emitted.
- [x] 3.2 Add source-level dominant bottleneck values for `capture-no-frame`, `publisher-no-connect`, `backend-no-receipt`, `asr-accepted-no-text`, and `web-no-consumer`.
- [x] 3.3 Ensure current session runtime ignores historical frame receipts, transcripts, and device events from older sessions.
- [x] 3.4 Add tests for synthetic PCM accepted with no real desktop frames reporting ASR reachable and desktop capture blocked.

## 4. Web Live Conversation

- [x] 4.1 Update live page empty state to show the current session's exact diagnostic stage instead of generic waiting copy.
- [x] 4.2 Render microphone transcripts as “我” and system transcripts as “面试官” from backend role mapping only.
- [x] 4.3 Allow single-channel realtime conversation when only microphone or only system output is working.
- [x] 4.4 Add regression tests that historical transcripts from another session are never displayed in the current live page.

## 5. Remote Screenshot Answer Pipeline

- [x] 5.1 Add backend capture request stages for requested, claimed, capture-failed, uploaded, vision-running, completed, failed, and cancelled.
- [x] 5.2 Update desktop companion to claim screenshot requests and report exact failure stage and message.
- [x] 5.3 Add desktop screenshot capture validation that checks selected screen availability before upload.
- [x] 5.4 Update web screenshot modal to show request stage and actionable errors for backend unavailable, desktop not connected, desktop capture failed, upload failed, and vision failed.
- [x] 5.5 Add tests for no active desktop binding preventing remote screenshot request creation.

## 6. Packaging and Permissions

- [x] 6.1 Update macOS release packaging to verify native runtime files and permissions descriptions are included.
- [x] 6.2 Keep `desktop:reset-privacy-open` for local ad-hoc builds and document why formal Developer ID signing is required for commercial releases.
- [x] 6.3 Add a packaged-app diagnostic that confirms microphone, system output, and screen capture can all be requested from the same app identity.

## 7. End-to-End Verification

- [x] 7.1 Run backend-only ASR synthetic PCM probe and record accepted/timeout/suppressed results.
- [ ] 7.2 Run packaged desktop real microphone test and verify backend `frameReceipts > 0` for microphone.
- [ ] 7.3 Run packaged desktop local playback/system-output test and verify backend `frameReceipts > 0` for system output or explicit unsupported diagnostic.
- [ ] 7.4 Run web live page test and verify realtime conversation displays current session transcript.
- [ ] 7.5 Run screenshot answer test and verify request reaches completed state with an answer, or fails with a specific stage error.
- [x] 7.6 Update docs with the exact local runbook and known macOS/AirPods limitations.
