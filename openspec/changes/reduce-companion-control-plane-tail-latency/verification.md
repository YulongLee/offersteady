# Verification

## Local results

- `npm --workspace @offersteady/desktop test`: 31 files, 174 tests passed.
- `npm --workspace @offersteady/desktop run typecheck`: passed for main and renderer.
- `npm --workspace @offersteady/desktop run build`: passed for Electron main and Vite renderer.
- `PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_admin_capacity.py -q`: 8 passed.
- `PYTHONPATH=apps/backend python -m pytest apps/backend/tests -q`: 388 passed, 14 skipped, 1 existing timing-sensitive ASR concurrency assertion failed by 16ms under full-suite load.
- Isolated rerun of the timing-sensitive assertion: 1 passed.
- `openspec validate reduce-companion-control-plane-tail-latency --strict`: passed.

All tests use synthetic state and timing data; no user audio, transcript, screenshot, answer or identity content was recorded.

## Release artifacts

- Aligned 1.2.13 macOS arm64, macOS x64 and Windows x64 artifacts were built and uploaded to immutable OSS paths.
- Both macOS artifacts passed signing, App/DMG notarization, stapling and Gatekeeper verification.
- The Windows NSIS installer passed payload and x86-64 executable validation under the existing unsigned distribution policy.

## Production checks

- Active interview count was zero before replacing only the Backend container.
- Backend health, Web state and build endpoints passed; PostgreSQL, Redis, Web, Admin and Analytics were not replaced.
- The public release manifest reported all three platforms at 1.2.13 and all byte-range download probes returned HTTP 206 with matching totals.
- A privacy-safe post-rollout sample contained 552 requests, ordinary API P95 294.15ms, P99 441.41ms and zero 5xx responses.
- The previously observed headline P95 was about 2.94s, but it included long-lived screenshot SSE durations. The new ordinary API number excludes those streams by design, so the two values verify the corrected metric boundary rather than proving an equivalent workload speedup.
- Old 1.2.12 companions still produce the old request cadence. Request-rate reduction must be evaluated after 1.2.13 client adoption; live 2-second lease refresh is intentionally preserved.
