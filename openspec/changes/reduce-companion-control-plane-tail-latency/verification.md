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

## Release checks pending

- Verify aligned 1.2.13 macOS arm64, macOS x64 and Windows x64 artifacts.
- Confirm production interview activity before Backend replacement.
- Smoke test health, Web state, release manifest and download byte ranges.
- Compare control-plane request rate, ordinary API P95 and errors after rollout.
