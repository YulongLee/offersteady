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

- Backend: 247 passed, 13 skipped.
- Web: 263 passed.
- Desktop: 59 passed.
- Workspace typecheck: passed.
- Production build with guarded environment: passed.
