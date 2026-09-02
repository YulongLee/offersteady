# Realtime Control Plane P0 Baseline

- Git commit: `dfc3ca83246fe803756aae55f82e55562a30b9d6`
- Git tag: `baseline-realtime-control-plane-p0-20260903`
- Production Backend image: `sha256:2ef612b83287ed758baccd1f3d2230186efd26771039b05b3386091e9bc4da44`
- Production Backend container before rollout: `2143453806aaaca7bf7a41efd8f6e041c15c2502fda6946bba605374bdab1b55`
- Container start: `2026-09-01T22:08:01.662001536Z`

The baseline image, Git tag and legacy Redis keys must remain available until the P0 production observation window passes. Rollback restores this image/commit without deleting PostgreSQL or Redis data.

## Production rollout

- Candidate commit: `7e47d39ae1d4e13d681867de025ad25446b954de`
- Candidate Backend image: `sha256:98334bef1f96cdb09b2f93de99dcc56580201b701e0614d20e378739258f2cec`
- Switched only after active interviews and recent audio activity both reached zero.
- First steady window: 333 ordinary requests, P50 `70.66 ms`, P95 `325.42 ms`, P99 `416.27 ms`, max `495.57 ms`, zero 5xx.
- Second steady window with realtime audio active: 328 ordinary requests, P50 `87.88 ms`, P95 `459.75 ms`, P99 `580.07 ms`, max `823.35 ms`, zero 5xx.
- Redis global snapshot writes remained zero after rollout; entity updates and realtime events continued normally.
- Baseline image tag and legacy Redis state remain intact for immediate rollback during user acceptance.
