# Global Performance Parity Release — 2026-10-11

- Release: `20261011-global-performance-parity-1`
- Scope: Global backend container only; no CN, Web, Admin, worker, database, Redis, or companion-program change.
- Candidate source: `/opt/offersteady-global/releases/20261011-global-performance-parity-1`, copied from the running `20260929-global-web-entry-1` release.
- Candidate image: `offersteady-global-backend:20261011-global-performance-parity-1`
- Candidate image digest: `sha256:54e8e804a8bd8a39ad0adf91d7db414add952153ee8914482dac5b9df8a3a688`
- Rollback image: `offersteady-global-backend:practice-20260929-1` (`sha256:093b86c1e32a8b02774e60eabed17b8ba0bff629da7ab239d8f48ba6670ee991`)

## Verification

- OpenSpec strict validation: passed.
- Candidate compile check: passed after removing only `._*` packaging metadata from the candidate directory.
- Focused tests: 42 passed, 1 dependency deprecation warning, 0 failures.
- Isolated image smoke test: passed; configuration loaded `realtime_desktop_heartbeat_write_min_interval_seconds=10.0` and request breakdown produced telemetry P95.
- Idle gate 1: all zero at `2026-10-11T04:46:58Z`.
- Idle gate 2: all zero at `2026-10-11T04:47:10Z`.
- Backend health after deployment: HTTP 200, version `20261011-global-performance-parity-1`, environment `production`.
- Public `https://offersteady.com/healthz`: HTTP 200 with the same backend version.
- Runtime module smoke after deployment: `RequestWindow` exposed separate user/telemetry P95 values and bounded `slowRoutes`.
- Public Web manifest intentionally remained `20260929-global-web-entry-1` because this change deploys no Web code.
- Existing Web/Admin/worker/Postgres/Redis container start times remained unchanged.

## Rollback

The previous backend image remains locally tagged and can be restored by recreating only `offersteady-global-backend-1` with `offersteady-global-backend:practice-20260929-1` using the prior release compose overlay.
