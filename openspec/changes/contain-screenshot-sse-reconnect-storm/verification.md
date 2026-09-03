# Verification

## Baseline

- Recorded at: 2026-09-04 (Asia/Shanghai)
- Git commit: `7bcc480d0f7b3a967e623c7c5463161924c0a3a3`
- Production Backend container: `8e402f66e2d48c709cbf6d5af712fcfc65123d83170319e80e9a07b04b798489`
- Production Backend image: `sha256:98334bef1f96cdb09b2f93de99dcc56580201b701e0614d20e378739258f2cec`
- Production Backend started: `2026-09-02T17:58:39.661752571Z`
- Baseline state: healthy, restart count 0

The running container image, not the mutable local `compose-backend:latest` tag, is the authoritative rollback target. No production process was changed while recording this baseline.

## Local verification

- Focused coordinator, route, screenshot, billing, realtime, and control-plane regression: `69 passed`.
- New screenshot admission suite: `9 passed`.
- Python bytecode compilation: passed.
- Git whitespace validation: passed.
- OpenSpec strict validation: passed.
- First full Backend run: `444 passed, 20 skipped, 1 failed`; the sole failure was an unrelated wall-clock prewarm threshold under suite load. The same test then passed five consecutive isolated runs without changing its threshold or implementation.
- Second full Backend run: `446 passed, 20 skipped, 1 failed`; the same pre-existing wall-clock assertion measured `355.42 ms` against `350 ms`, while the Backend request log measured `180.38 ms`. All other tests passed.
- Synthetic in-process admission storm: `100000` attempts, active work remained `1`, `0` simulated 5xx responses, admission P50 `0.0005 ms`, P95 `0.0005 ms`, P99 `0.0006 ms`.
- Synthetic HTTP storm with in-memory dependencies: `5000/5000` abnormal streams returned HTTP 409 with zero 5xx; `500/500` concurrent ordinary health requests returned HTTP 200 with P50 `16.64 ms`, P95 `27.13 ms`, P99 `224.76 ms`, and zero 5xx. Active screenshot stream work remained `1`.

## Production rollout

Pending zero-active-interview and zero-active-audio gate.
