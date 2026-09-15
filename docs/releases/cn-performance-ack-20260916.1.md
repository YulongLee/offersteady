# CN performance acknowledgement hotfix — 2026-09-16

## Scope and cause

The Chinese runtime mixed a newer `/realtime-speech/sessions/{id}/performance-ack` route with an older `RealtimeSpeechService.acknowledge_runtime_timing` implementation. The route always passed three optional entry timestamps even when omitted by the browser; the older service signature raised `TypeError` before session lookup. Between 01:18 and 01:25 CST, 124 HTTP 500 responses were observed, all on this endpoint. This was a deployment regression, not provider failure or resource exhaustion.

The repair restores three optional parameters, their content-free diagnostic mappings, and their three existing summary distributions: nine added lines in one runtime file. It does not modify the answer model, prompts, billing, UI, database schema, memory reclamation, or Global deployment.

## Actual deployment baseline

- Source: `/opt/offersteady/releases/20260915-cn-memory-cleanup-1` (resolved production symlink).
- Previous image: `sha256:9f18292364961331e42f5ffdd285400b6bcdfc432cdd7d10e8c6783ab9a2dbce`.
- Previous source SHA256: `5b11eab3d7bd180a7d8d71b65547dc87dea1bc5aa813376aa9c033f902d5b6c3`.
- Candidate/deployed image: `sha256:1b9cc8317eda3057dc5fd5344ccc2386d8470e597cc425f20cb412e1f761bfb6`.
- Repaired source SHA256: `1edf03fefad8e1dacb974e9cded66e8bd0b5d4d7919d1f324fce8192eca56702`.
- New Backend container started at `2026-09-16 01:34:09 +08:00`; healthy at `01:34:26`.

The candidate derives from the exact running image, adds only the repaired Python source layer, and preserves runtime dependencies, environment, command and ports. The host source was synchronized to that exact repaired file. `main.py`, `core/config.py`, and the realtime route hashes remained unchanged. Only `compose-backend-1` was recreated with `--no-deps --no-build`.

The environment's app-version string still reads `cn-session-reclamation-20260911.1`; identify this hotfix by the image/source hashes above, not that older display label or Git HEAD. The main developer worktree already had the corrected timing logic and unrelated modifications; it was NOT copied over production.

## Verification

- Extracted source from the running container to an independent local directory and verified matching host/container hashes.
- [New regression test](../../apps/backend/tests/test_runtime_performance_ack_compatibility.py) reproduced the error before repair: all four valid telemetry stages, omitted/null/populated timing payloads failed with 500.
- After repair: six test methods and 16 subtests passed. Tests exercise the real FastAPI route, real service acknowledgement/trace storage/summary, with synthetic identity and session lookup only; no provider calls or real user data.
- A wider selection against the production source snapshot passed: 13 tests, 16 subtests. The old image's test harness required entering the application lifespan; its stream-event assertion also lacked three fields already present in its runtime route. The isolated harness entered lifespan, and the assertion was synchronized to the current repository's existing explicit field and ordering assertions. No production code was changed to bypass those tests.
- The same six compatibility tests passed inside the candidate image with `--network none`, no production environment, read-only filesystem, bounded CPU/memory and a read-only synthetic test mount.
- Main-worktree regression: six tests and 16 subtests passed independently.
- Before switch: database live-session count = 0, active desktop transports = 0, active provider sessions = 0 on both channels, no queued audio, active/pending answers = 0, active screenshot streams = 0.
- Strict OpenSpec validation passed for `fix-cn-performance-ack-compatibility`.
- Post-deploy: source/image hashes and health checked; initial live access log sample had no 5xx. No new real-user performance acknowledgement had occurred yet. Do not confuse idle error-rate recovery or an isolated test with end-to-end real-user acceptance.
- At 01:35:16 CST, the saved monitoring sample showed API error rate 0.0%, API P95 43.53 ms, 221 control API requests and zero active interviews. These are post-restart idle observations, not a load test.

## Rollback artifacts

Server-only directory: `/opt/offersteady/hotfixes/20260916-cn-performance-ack-1` (root-only access).

It contains an independent original Python file, prior Compose file, repaired file, Dockerfile, isolated test and guarded deployment script. Original image is retained as `offersteady-backend:cn-before-ack-20260916-1`; repaired image is `offersteady-backend:cn-performance-ack-20260916-1` and currently also `compose-backend:latest`.

Rollback requires another idle-workload check, restoring the original source and retagging the retained old image as `compose-backend:latest`, then recreating only Backend with the unchanged production Compose/environment configuration. The prior image still has the acknowledgement bug; rollback is only a fallback for a new regression. No database rollback or user-data deletion is involved.
