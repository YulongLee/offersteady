# CN independent quick-answer completion — 2026-09-23

## Scope

User-authorized CN deployment of the locally verified independent simple-answer completion fix. Simple text is streamed first and finalized before waiting for detailed retrieval/search. Detail keeps its own loading state; completed simple text survives detail failure or interrupted delivery. Cancellation, duplicate submission protection, model settings, billing and provider timeouts remain unchanged.

No database migration, production environment edit, payment configuration change, Admin release, companion update or Global deployment was performed.

## Baseline and release

- Previous source: `/opt/offersteady/releases/20260923-cn-web-nothink-1`.
- Current source: `/opt/offersteady/releases/20260923-cn-quick-stage-1`.
- Current pointer: `/opt/offersteady/current`.
- Backend: `offersteady-cn-backend:quick-stage-20260923-1`, image `sha256:95f82840da434afc99c7b9c7fc76663f32acd0b4d81a2c855792372beb5385ae`.
- Web: `offersteady-cn-web:quick-stage-20260923-1`, image `sha256:e20b47119c955b51d4df94daf6628033ff217f8b850dbb20e442831a1ecb3a21`.
- Local candidate: `/tmp/offersteady-cn-quick-stage-qXmeXf`.

The candidate was assembled from running CN source. Eleven runtime source files changed: four backend files (`ports/chat.py`, `schemas/live_answer.py`, `modules/live_answer.py`, `services/chat_service.py`), six Web files (`AnswerWorkspace.tsx`, `LivePage.tsx`, `backend-adapter.ts`, `domain.ts`, `live-answer-stream.ts`, `live-workspace.ts`) and `packages/protocol/src/answer.ts`. Diffs were checked against the CN baseline before copying. Images layer the selected backend files and rebuilt Web artifacts onto retained production images. Existing static media and prior hashed assets remain available.

Production environment, Compose file, backend Settings and web-search gateway compared byte-for-byte with the previous release. Unrelated local PDF, worker, homepage and other workspace changes were not included.

## Verification

- Candidate backend focused suite: **57 passed**.
- Candidate foundation live-answer subset: **12 passed**.
- Candidate frontend focused suite: **122 passed** across six files.
- Type-checked production Web build: passed; manifest remains production with same-origin API `/`.
- Strict OpenSpec validation and whitespace check: passed.
- Network-disabled candidate container: **five mocked scenarios passed** — web success, web fallback, ordinary answer, cancellation at quick completion, and actual HTTP SSE serialization. No real user data or paid provider request was used.
- Candidate Nginx configuration: passed.
- Rollback decoder check: passed with a new-format synthetic task record.

The isolated CN foundation test harness was configured to run the application lifespan and use an explicit synthetic provider URL/model, as in the previous CN release validation. An initially omitted pytest import was corrected in the test-only harness, then all 12 tests passed. Test fixtures were not deployed. This is not a claim that the full repository suite was run or that provider latency has decreased.

## Safe-switch gate and outcome

At 03:46 and 03:48 Asia/Shanghai, one live interview and one live-page lease remained, so the running service was not changed. At 03:50:57 they had cleared. Immediately before switching, **2026-09-23 03:51:33 Asia/Shanghai**, all four gates were zero:

- Live interviews: **0**.
- Unexpired live-page leases: **0**.
- Audio tracks receiving frames in the preceding 30 seconds: **0**.
- Unfinished answer tasks: **0**.

Only Backend and Web were recreated. Backend started at 03:51:35 and became healthy; Web started at 03:51:51. Both restart counters were zero. Existing Admin/material-worker/analytics/promotion-analytics container start times stayed unchanged; historical worker restart counters were not reset.

Post-switch public `/`, `/app`, `/healthz`, `/api/v1/web/state`, `/api/v1/billing/status` and `/offersteady-build.json` all returned **HTTP 200**. The public entrypoint references `main-Cy_JSF7y.js`; downloaded `LivePage-Baraz3fm.js` and `AnswerWorkspace-CVbUY-KI.js` matched the tested artifacts by SHA-256. All four running backend file hashes matched the candidate. In-process schema conversion confirmed `quick-completed` carries `quickAnswerCompleted=true` while the task stays streaming; no task was persisted by this check.

Initial post-start backend observation: **79 log lines, 0 ERROR/CRITICAL/traceback lines**. This is a short post-release check, not ongoing monitoring. Real interview/provider acceptance remains for the user.

## Compatibility-safe rollback

The added task field is serialized in Redis. Do not blindly restore the old backend image, whose decoder does not accept the new field. A retained rollback image contains only the additive dataclass field on top of the former production backend; it keeps the previous behavior while reading new task records.

- Rollback source: `/opt/offersteady/releases/20260923-cn-quick-stage-rollback-1`.
- Backend rollback: `offersteady-cn-backend:quick-stage-rollback-20260923-1`, image `sha256:bd7aa3e29fc864c7e785889d87aeab5ab05928c7c7021bcd5d04dcb12c129bf0`.
- Web rollback: `offersteady-cn-web:quick-stage-rollback-20260923-1`, image `sha256:cac168af1c8c64ba460039615ba6a2a0a12fbef0d45891bd88ff78d3c95542f8`.

Recheck all activity gates before a rollback. Do not stop a customer interview, clear Redis or remove database volumes.

```sh
docker exec -i -w /app/apps/backend compose-backend-1 python - < /opt/offersteady/releases/20260923-cn-quick-stage-1/deploy/check-idle.py
# Continue only if the gate exits successfully with all counts zero.
docker tag offersteady-cn-backend:quick-stage-rollback-20260923-1 compose-backend:latest
docker tag offersteady-cn-web:quick-stage-rollback-20260923-1 compose-web:latest
ln -sfn /opt/offersteady/releases/20260923-cn-quick-stage-rollback-1 /opt/offersteady/current
cd /opt/offersteady/current
docker compose -p compose --env-file .env.production -f infra/compose/docker-compose.foundation.yml up -d --no-build --no-deps backend web
```

Recheck health and public endpoints after rollback. The release switch script also retains this compatibility-safe rollback path for failed immediate health checks.
