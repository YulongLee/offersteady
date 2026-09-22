# CN web-answer switching fix — 2026-09-23

## Scope

User-authorized CN deployment of the locally verified fix for ordinary quick answers failing after web mode is switched off.

- Distinct per-attempt, mode-aware billing request IDs; in-flight duplicate protection retained.
- Switching web mode off cancels/detaches the current web answer, retains generated simple-answer text with an incomplete warning, and immediately unlocks ordinary quick answer.
- Obsolete stream/realtime results and cleanup callbacks cannot overwrite the next answer.
- Backend cancellation survives a delayed search result; disconnect cleanup releases unfinished-task reservations.
- Failed/cancelled retries issue a fresh request; truncated SSE reports a recoverable failure.

No model, pricing, provider timeout, production environment, payment settings, database migration, Admin, or desktop companion change was included. International service was not deployed.

## Baseline and artifacts

- Previous CN release: `/opt/offersteady/releases/20260923-cn-web-search-1`.
- Current CN release: `/opt/offersteady/releases/20260923-cn-web-toggle-fix-1`.
- Current symlink: `/opt/offersteady/current`.
- Backend image: `offersteady-cn-backend:web-toggle-fix-20260923-1`, ID `sha256:a59c0cd153fe1af6e068353c2e1965a5749b817b4c97aabbc33159bdf1f1df54`.
- Web image: `offersteady-cn-web:web-toggle-fix-20260923-1`, ID `sha256:cac168af1c8c64ba460039615ba6a2a0a12fbef0d45891bd88ff78d3c95542f8`.
- Retained rollback image tags: `offersteady-cn-backend:rollback-20260923-web-toggle-1` and `offersteady-cn-web:rollback-20260923-web-toggle-1`.

The release candidate was assembled from the current CN source, not the entire dirty local workspace. Only seven runtime files differ: `LivePage.tsx`, `AnswerWorkspace.tsx`, `backend-adapter.ts`, `live_answer.py`, `chat_service.py`, `chat_repository.py`, and `redis_live_task_repositories.py`. The only additional chat-service difference from that baseline is an explanatory docstring for the existing quick-heading behavior.

Images layer the changed backend files and rebuilt Web artifacts onto retained running-image baselines, preserving unrelated runtime files and configuration. Environment, Compose, and backend Settings source were compared byte-for-byte before switching. Only Backend and Web containers were recreated.

## Release-candidate verification

- Six focused frontend files: **112 passed** on the CN baseline. The broader local workspace previously had 113; its unrelated extra baseline test was not added to the release candidate.
- Six focused backend files: **49 passed**.
- Foundation live-answer subset: **12 passed, 85 deselected**.
- Web typecheck, production build, backend compilation, and Nginx configuration validation: passed.
- OpenSpec strict validation and Git whitespace/error check: passed.

The foundation test harness initially omitted application startup, yielding unavailable-executor failures on the CN baseline. The release-only test harness was corrected to enter the real TestClient lifespan. A gateway-contract test also required an explicit synthetic base URL/model because the isolated candidate intentionally has no developer `.env`. With these test-only inputs, the 12 tests passed; no production startup/configuration code was changed to accommodate tests. Tests use synthetic data and mocked providers. These test-harness files were not deployed.

The broader pre-release local suite failures remain documented in [the local verification record](../../openspec/changes/add-web-grounded-detailed-answer/verification.md); this release does not claim an entirely green full-project suite.

## Deployment gate and checks

Immediately before switch, at approximately **2026-09-23 03:00:51 Asia/Shanghai**:

- Database sessions with `status = 'live'`: **0**.
- Unexpired live-page heartbeats: **0**.
- Audio tracks with accepted/pending frames in the previous 30 seconds: **0**.

Backend started at **03:01:02**, became healthy, and Web subsequently started. A brief 502 window occurred during container replacement; checks passed after Web startup. Post-switch checks:

- Public homepage, `/app`, `/healthz`, `/api/v1/web/state`, and `/api/v1/billing/status`: **HTTP 200**.
- Build manifest: production environment, same-origin API `/`.
- Public entrypoint uses `main-Dufgn3xh.js`; served `LivePage-Qh3Lv_rf.js` SHA-256 matches the tested artifact: `a03c6e18d4aa5fafcc60abca879c99901bac62a6e74bdfc73c9d1750c0d27c59`.
- Four deployed backend source hashes match the tested candidate.
- Backend/Web running, restart count **0**; other service containers retained their existing uptime.
- Initial post-start backend observation: no ERROR, CRITICAL, or traceback entries. Follow-up Web access snapshot: 81 HTTP 200, 2 HTTP 409, 6 HTTP 404, and **no HTTP 5xx**. The 4xx routes were session heartbeats and desktop binding/capture polling; this is not a claim that all requests returned 200.
- Rechecked after switch: live interviews/pages/recent audio were all 0.

Real user acceptance of “web on → answer → web off → ordinary quick answer”, including real provider latency and billing, remains for the user. No live user interview or paid provider call was created for deployment verification.

## Rollback

Before a manual rollback, recheck the live-interview gate and obtain a safe maintenance window. Keep the database and Redis volumes unchanged.

```sh
docker tag offersteady-cn-backend:rollback-20260923-web-toggle-1 compose-backend:latest
docker tag offersteady-cn-web:rollback-20260923-web-toggle-1 compose-web:latest
ln -sfn /opt/offersteady/releases/20260923-cn-web-search-1 /opt/offersteady/current
cd /opt/offersteady/current
docker compose -p compose --env-file .env.production -f infra/compose/docker-compose.foundation.yml up -d --no-build --no-deps backend web
```

Recheck public endpoints and container health after rollback. Do not run `down -v`, clear Redis, or replace regional configuration.
