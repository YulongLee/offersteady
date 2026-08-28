# Verification

Verified on 2026-08-28 before local physical acceptance.

## Passing checks

- Desktop focused audio regressions: 43 passed.
- Desktop full suite: 164 passed; typecheck passed; build passed.
- Backend focused realtime receiver suite: 25 passed.
- Protocol full suite: 31 passed; typecheck passed; build passed.
- Web focused transcript and reconnect suites: 66 passed.
- Web typecheck passed.
- Web production build passed with `VITE_APP_ENV=production`, `VITE_API_BASE_URL=/`, and public version `1.2.10`.
- `openspec validate deliver-perceived-realtime-transcripts-1-2-10 --strict` passed.
- `git diff --check` passed.

## Existing unrelated failures observed in full suites

- Backend full suite: 343 passed, 14 skipped, and one timing-bound test failed under full parallel load because elapsed time exceeded its 350 ms assertion. The same `test_live_start_bounds_provider_prewarm_wait` test passed when rerun alone. No code in this change modifies provider prewarm waiting.
- Web full suite: 307 passed and one existing material-actions assertion failed because it still expects the removed legacy backend-connection copy. The same failure reproduced before this change and is outside realtime transcript delivery.

No production artifact was published by these checks.
