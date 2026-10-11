## Why

The Global release runs on a separate release stream. A read-only comparison with the running Global backend found that its web heartbeat still performs full session reads and its desktop heartbeat persists unchanged payloads on every heartbeat. These repeated database and Redis operations add avoidable tail latency and make capacity diagnostics less comparable with the approved CN performance baseline.

## What Changes

- Use a five-field authoritative session projection for normal Global web heartbeats, while preserving lease refresh, idle expiry, and ended-session behavior.
- Coalesce unchanged desktop heartbeat writes in-process, bounded by a 10-second minimum persistence interval (and never longer than half the lease TTL); persist immediately for first registration and material changes.
- Preserve and regression-test the existing Global request-breakdown/P95 fields so slow routes can be separated from telemetry traffic.
- Build and deploy only a Global backend release from the current running Global image, with an idle-interview gate and a rollback path.

## Capabilities

### New Capabilities

- `global-performance-parity`: Reduce repeated heartbeat I/O and keep request-level P95 diagnosis available in the Global release.

### Modified Capabilities

- None.

## Impact

- Backend service code, configuration, and focused regression tests only.
- No database migration, client protocol change, companion-program upgrade, frontend behavior change, billing change, or model/ASR/TTS change.
- Deployment is limited to the Global backend container; the existing image remains available for rollback.
