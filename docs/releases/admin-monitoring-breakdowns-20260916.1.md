# Admin monitoring breakdowns · 2026-09-16

## Scope

Adds privacy-safe request diagnostics to the admin capacity view. This release is additive and does not change interview, ASR, screenshot, provider, or answer-generation behavior.

## Included

- Stable normalized routes with query strings and dynamic identifiers removed.
- Separate rolling summaries for user API, telemetry, recovery snapshots, and SSE duration.
- Bounded slow-route list with P95, request count, and 5xx count.
- Existing aggregate capacity fields retained for older admin clients.
- Dashboard panel falls back cleanly when an older backend omits the new fields.

## Validation

- Backend focused monitoring and lifecycle tests pass.
- Admin typecheck, focused tests, and production build pass.
- OpenSpec strict validation passes.

## Deployment note

Deploy the backend and admin images together after an authenticated capacity smoke check. Keep the currently deployed images as rollback targets; no database migration is required.
