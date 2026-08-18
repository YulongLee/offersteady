# Verification

## Synthetic latency evidence

| Stage | Before | After | Evidence |
| --- | ---: | ---: | --- |
| System-audio silence finalization | 650 ms | 500 ms | Desktop segmenter constants and boundary regression test |
| Microphone silence finalization | 850 ms | 700 ms | Desktop segmenter constants and boundary regression test |
| 100-character partial transcript catch-up | 1,600 ms (2 chars every 32 ms) | at most 192 ms | Adaptive catch-up regression test completes in six 32 ms ticks |
| Confirmed question audio-worker occupancy | Full answer duration; local sample 4.13 s | under 250 ms | Blocking synthetic model regression verifies ingest returns before model completion |
| Automatic answer visibility | Only after full completion | First provider chunk | Automatic stream and web reconciliation regression tests |

The answer model, ASR provider, prompts, billing rates, page layout, and user controls are unchanged. Provider first-token latency still depends on the configured model and network; production health verification is recorded during deployment.

## Test evidence

- Backend: 249 passed, 13 skipped.
- Web: 263 passed.
- Desktop: 59 passed.
- Workspace typecheck: passed.
- Production build with guarded environment: passed.

## Production release evidence

- Runtime commit: `154516428e5b92f63c138c2dc91ee07a0b6a718e`.
- Public `/healthz`, billing status, Web state, and homepage: healthy after container replacement.
- Five consecutive public `/healthz` checks returned HTTP 200 in 90-100 ms; the homepage returned HTTP 200 in 101 ms.
- Database-backed session validation is limited to once every two seconds per event stream while Redis event delivery remains at 100 ms. After the release, local health checks completed in 4-5 ms and the observed backend/PostgreSQL CPU usage was approximately 6%/0%.
- Concurrent cold-start repository construction is single-flight; the post-restart desktop reconnect window produced no traceback or PostgreSQL deadlock.
- Desktop release manifest: macOS arm64, macOS x64, and Windows x64 all published as `0.1.13`.
- All three public download routes return a signed-URL redirect.
- Post-deploy backend log scan found no traceback, deadlock, or automatic-answer failure.
