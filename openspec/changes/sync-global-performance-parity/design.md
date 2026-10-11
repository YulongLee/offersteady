## Context

Global and CN are deployed from separate release streams. The running Global service already exposes richer request-breakdown telemetry, but its heartbeat paths do more work than the approved CN performance baseline. The change must be safe to roll out while preserving the existing client contract.

## Goals

- Reduce per-heartbeat database/Redis work without changing the heartbeat response shape or lease semantics.
- Keep desktop presence fresh to callers while bounding durable writes for unchanged heartbeats.
- Make the P95 dashboard data sufficient to distinguish user API work from telemetry work.
- Produce a reproducible, reversible Global release from the actual running Global source/image.

## Non-goals

- No changes to companion binaries, web UI, API routes, authentication, billing, model selection, audio, or interview lifecycle policy.
- No database schema or index migration.
- No attempt to normalize unrelated CN/Global release drift in this change.

## Design

### Web heartbeat projection

Add a repository/session-service projection containing only `session_id`, `owner_user_id`, `status`, `started_at_ms`, and `last_activity_at_ms`. The normal web heartbeat uses this projection for idle/ended checks, touches the activity lease, and avoids material, conversation, resume, billing, or full-session reads. Expired and ended sessions retain the existing 409 behavior.

### Desktop heartbeat write coalescing

Track the last durable write per device in the realtime speech service. The first registration and any material change (display name, capabilities, or offline status) persist immediately. An unchanged online heartbeat returns a fresh in-memory device view but skips persistence until the configured minimum interval (10 seconds by default, capped at half the heartbeat TTL). This preserves caller-visible freshness while reducing repeated Redis writes.

### Capacity diagnostics

Keep the existing Global `requestBreakdown`, `userApiP95Ms`, `telemetryP95Ms`, and `slowRoutes` response fields. Add regression coverage rather than changing the already richer implementation.

### Release and rollback

Create a candidate from the current running Global backend image/source, overlay only the approved files, run focused tests and static checks, then build a new backend image. Require two consecutive idle gates before deployment. Recreate only the backend container, verify health/config/metrics, and retain the previous image/tag for immediate rollback.

## Risks and mitigations

- A projection that omits a field could alter expiry behavior: cover status/timestamps with focused tests and retain the existing error mapping.
- In-process coalescing state is lost on restart: first heartbeat after restart persists, and the lease TTL bounds the skip interval.
- Multi-worker processes have independent coalescing maps: this is safe (at worst more writes) and does not affect correctness.
- A release built from the wrong stream could regress Global: compare image/source/version markers before build and verify the public Global manifest after deployment.
