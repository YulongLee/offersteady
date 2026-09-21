## Why

Production diagnostics showed that content-free `performance-ack` requests can dominate request volume during a live interview. Each subtitle render acknowledgement performed a full session/material lookup, so diagnostic traffic increased ordinary API tail latency as user count grew.

## What Changes

- Sample non-final transcript-render acknowledgements at most once per session window while retaining final revision telemetry.
- Reuse a short-lived, process-local ownership check for transcript-render acknowledgements instead of rereading the full session and bound materials for every sample.
- Remove per-ack INFO log writes and expose privacy-safe cache counters for verification.
- Preserve answer generation, ASR, transcription, screenshot assistance, billing and user-visible interview behavior.

## Impact

- Web telemetry request volume and backend work decrease.
- Performance diagnostics become sampled rather than recording every intermediate subtitle repaint.
- No audio, transcript, screenshot or personal content is persisted by this change.
