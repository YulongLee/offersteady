## Why

The admin dashboard currently exposes an aggregate API P95, which mixes user-facing control requests with telemetry, heartbeats, and long-lived streams. During an interview burst this can make a small number of background requests look like a broad user-facing outage and makes the slow route difficult to locate.

## What Changes

- Add privacy-safe request-class and normalized-route breakdowns for latency, request count, and 5xx rate.
- Separate user-facing API quality from background telemetry (performance acknowledgements, heartbeats, and device polling).
- Keep long-lived SSE duration visible as its own metric instead of mixing it into ordinary request P95.
- Expose a bounded, recent breakdown in the admin capacity response and render it in the existing dashboard style.
- Add regression coverage for route normalization, classification, rolling-window aggregation, and dashboard serialization.

## Capabilities

### New Capabilities

- `admin-monitoring-breakdowns`: Provides actionable, privacy-safe API latency and error breakdowns for the admin dashboard.

### Modified Capabilities

<!-- No existing OpenSpec capability requirements are changed. -->

## Impact

- Backend request monitoring and the admin capacity response.
- Existing admin dashboard data adapter and monitoring cards; no visual redesign.
- No new external dependency, user data persistence, AI prompt, model, ASR, or interview behavior change.
