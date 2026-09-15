## 1. Monitoring attribution

- [x] 1.1 Classify `/api/v1/admin/*` as telemetry and add regression coverage.
- [x] 1.2 Verify existing user/telemetry/SSE P95 fields remain compatible.

## 2. Safe read-path improvements

- [x] 2.1 Add a partial live-session activity index for the highest-frequency active-session read path without changing its contract.
- [x] 2.2 Add fallback and compatibility tests.

## 3. Verification

- [x] 3.1 Run focused backend/admin tests, typecheck and build.
- [x] 3.2 Validate OpenSpec and document non-deployment status.
