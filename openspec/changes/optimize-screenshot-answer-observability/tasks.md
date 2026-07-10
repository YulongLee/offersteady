## 1. Backend Telemetry

- [x] 1.1 Add metadata-only timing fields for remote screenshot capture requests and screenshot answer tasks.
- [x] 1.2 Instrument backend phases for upload accepted, image optimization, OSS write, signed URL generation, vision model call, answer persistence, and total background processing.
- [x] 1.3 Ensure failed upload, OSS, signing, vision, and persistence phases store a failed stage and error code without raw screenshot content.
- [x] 1.4 Expose telemetry in screenshot answer API responses while keeping existing response fields backward compatible.

## 2. Desktop Capture Metadata

- [x] 2.1 Ensure desktop full-screen capture continues to auto-compress screenshots before upload.
- [x] 2.2 Include compressed width, height, original width, original height, byte length, content type, and extension in desktop capture metadata.
- [x] 2.3 Preserve full-screen capture flow without adding manual crop or region selection UI.

## 3. Web Progress Experience

- [x] 3.1 Map backend remote screenshot stages to clear live interview UI messages.
- [x] 3.2 Show separate states for waiting for desktop, capturing, uploading, uploaded/recognizing, generating answer, completed, failed, and cancelled.
- [x] 3.3 Ensure retry and dismiss actions remain available for capture, upload, OSS, and vision failures.
- [x] 3.4 Confirm screenshot answer UI does not imply resume, JD, or knowledge base context was used.

## 4. Performance Self-Test

- [x] 4.1 Add a local performance command or script that accepts a screenshot image path and runs the full remote screenshot answer flow.
- [x] 4.2 Write performance reports to `artifacts/perf/` with per-phase timings, byte counts, dimensions, model name, request id, task id, status, and error code.
- [x] 4.3 Ensure performance reports do not include raw screenshot bytes, base64 image data, or screenshot-derived sensitive text.
- [x] 4.4 Include an analysis summary that separates model API time from controllable engineering time.

## 5. Verification

- [x] 5.1 Run backend screenshot answer regression tests.
- [x] 5.2 Run desktop typecheck.
- [x] 5.3 Run web typecheck or focused screenshot answer UI tests.
- [x] 5.4 Run OpenSpec validation for `optimize-screenshot-answer-observability`.
- [x] 5.5 Run the performance self-test with `/Users/liyulong/liyulong/3_test/test2.png` and report each phase duration plus remaining optimization opportunities.
