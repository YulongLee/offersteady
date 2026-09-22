# CN web-answer non-thinking release — 2026-09-23

## Scope

User-authorized deployment of explicit `reasoning: {"effort": "none"}` for web-grounded detailed answers. Only `apps/backend/app/services/web_search_gateway.py` changed at runtime (one parameter and an explanatory comment).

Ordinary quick/local detailed answer requests, models, output limits, 20-second web timeout, billing, environment, database, frontend, Admin, desktop companion, and international service were not changed. Non-thinking mode does not guarantee every web search completes within the timeout.

## Baseline and artifacts

- Previous release: `/opt/offersteady/releases/20260923-cn-web-toggle-fix-1`.
- New release: `/opt/offersteady/releases/20260923-cn-web-nothink-1`.
- Current symlink: `/opt/offersteady/current`.
- New backend image: `offersteady-cn-backend:web-nothink-20260923-1`.
- New image ID: `sha256:e11be574b4ae36afa87efbca488331277c918d7dc839e5d053fffc159de7a0e9`.
- Retained rollback image: `offersteady-cn-backend:rollback-20260923-web-nothink-1`, ID `sha256:a59c0cd153fe1af6e068353c2e1965a5749b817b4c97aabbc33159bdf1f1df54`.
- Deployed gateway SHA-256: `e382df112b85708e571849ad1d518c4cee63a917099a6632395acef7158db997`.

The image adds the gateway file to the verified running CN image. Removing the two added source lines yields the exact previous production file. Release source was copied from the current CN release; backend source, infrastructure, and prompt comparisons found no other runtime differences. Production environment and Compose files compare byte-for-byte with the previous release. No unrelated local workspace changes were uploaded.

## Verification and deployment gate

- Focused backend suite rerun: **52 passed**. Previous local foundation live-answer validation: **12 passed**, recorded in [local verification](../../openspec/changes/add-web-grounded-detailed-answer/non-thinking-verification.md).
- Isolated candidate image with networking disabled: success, provider timeout, and rejection payload/fallback checks all passed; web source extraction passed.
- OpenSpec strict validation passed.
- Immediately before switching, **2026-09-23 03:25:11 Asia/Shanghai**: live interviews **0**, unexpired live-page leases **0**, audio tracks receiving frames in the previous 30 seconds **0**, unfinished answer tasks **0**.
- Only backend was recreated; started at **03:25:13**, became healthy, restart count 0. All other existing service start times remained unchanged. Historical worker restart counters were not reset or modified.
- Public `/`, `/app`, `/healthz`, `/api/v1/web/state`, `/api/v1/billing/status`: **HTTP 200** after switching. Internal backend health/state/billing endpoints also returned 200.
- Initial post-start backend log check: no ERROR, CRITICAL, or traceback records.

## Synthetic provider smoke test

A synthetic public-documentation question was sent through the deployed gateway using existing production model credentials. No customer session, private material, or user billing reservation was created. The diagnostic provider call can incur ordinary provider usage.

- Actual outgoing `reasoning.effort`: `none`.
- Model: `deepseek-v4.1-flash`.
- Provider HTTP status: 200; gateway status: `succeeded`.
- Provider-reported reasoning tokens: **0**.
- Completed web-search calls: **2**; normalized sources: **5**.
- Duration: **9,407 ms**; no fallback.

This single gateway smoke test is not a browser end-to-end latency benchmark or a guarantee of future search availability. User acceptance remains to be performed in a real interview page.

## Rollback

Recheck live interviews, page leases, audio, and unfinished answers before rollback. Do not stop an active interview, clear Redis, modify database volumes, or replace regional configuration.

```sh
docker tag offersteady-cn-backend:rollback-20260923-web-nothink-1 compose-backend:latest
ln -sfn /opt/offersteady/releases/20260923-cn-web-toggle-fix-1 /opt/offersteady/current
cd /opt/offersteady/current
docker compose -p compose --env-file .env.production -f infra/compose/docker-compose.foundation.yml up -d --no-build --no-deps backend
```

Verify backend health and public endpoints after rollback.
