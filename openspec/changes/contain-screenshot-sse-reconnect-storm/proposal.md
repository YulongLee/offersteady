## Why

On 2026-09-03 a single desktop device produced a screenshot-request SSE reconnect storm that accumulated thousands of long-lived requests and delayed ordinary APIs, including `/api/v1/web/state`, by minutes. Client-side single-stream behavior in 1.2.13 reduces normal amplification, but production must also contain legacy or faulty clients without changing interview, transcription, answer, screenshot, billing, or UI behavior.

## What Changes

- Enforce a server-side, generation-safe single active screenshot-request stream for each desktop device binding.
- Reject or supersede duplicate stream attempts before they enter Redis blocking waits or realtime control executors, with bounded retry behavior compatible with legacy companions.
- Isolate screenshot stream waits from realtime transcript/session stream waits and cap both active work and pending admission.
- Preserve cursor replay and pending screenshot lookup so reconnect containment cannot lose a screenshot request or cause duplicate billing.
- Add content-free metrics for active streams, duplicate attempts, replacements, admission saturation, and executor queue pressure.
- Add legacy-client, reconnect-storm, normal screenshot, realtime audio/subtitle, quick-answer, billing, and rollback regression coverage.
- Deploy only the Backend after active interviews and active audio publishers are both zero, retaining the current image and Redis state for immediate rollback.

## Capabilities

### New Capabilities

- `screenshot-stream-storm-containment`: Defines per-device screenshot SSE ownership, bounded admission, resource isolation, replay correctness, observability, compatibility, and rollout safety.

### Modified Capabilities

None.

## Impact

- Backend: screenshot request SSE route, application runtime resources, content-free capacity diagnostics, and configuration defaults.
- Desktop: no required protocol or release change; current and legacy companions remain compatible.
- Redis: existing event and pending-request records remain authoritative; no user content or new persistent business data is introduced.
- Deployment: Backend-only candidate and rollback image; Web, Admin, Desktop artifacts, PostgreSQL, Redis, model settings, prompts, and billing configuration remain unchanged.
- Privacy: diagnostics contain only counts, durations, states, and hashed or omitted device identifiers; no audio, transcript, screenshot, question, or answer content is recorded.
