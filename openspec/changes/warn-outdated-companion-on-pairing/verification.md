# Verification

## Pre-deployment

- Focused tests: `npm run test -w @offersteady/web -- --run src/App.test.tsx src/platform.test.ts` — 40 passed.
- Full Web suite: `npm run test -w @offersteady/web` — 47 files, 349 tests passed.
- Production build: `VITE_APP_ENV=production VITE_API_BASE_URL=/ VITE_PUBLIC_APP_VERSION=0.1.0 npm run build -w @offersteady/web` — passed.
- Spec validation: `openspec validate warn-outdated-companion-on-pairing --strict` — passed.
- Diff hygiene: `git diff --check` — passed.

## Production deployment

- Deployment gate: database reported zero live, non-deleted interview sessions immediately before rollout.
- Scope: Web image only; Backend, PostgreSQL, Redis, Admin and analytics containers were not recreated.
- Deployed source commit: `6293094c91b228ed82470d307b83a0b7e965e0a3`.
- Deployed Web image: `sha256:76a23a1a4cc1845d382673cf9df60c634171eae2527b759d888861a67b117b50`.
- Rollback tag: `compose-web:rollback-6293094-pre`, image `sha256:1c86bb728c0343cd391f18044c1cbffc323439a286278ecc2fab79a0427f2299`.
- Production smoke checks: local Web, `https://mianshiwen.cn/`, `https://www.mianshiwen.cn/`, Backend health and preparation SPA route returned HTTP 200.
- Public build manifest remained production/same-origin; deployed main asset contains the update-reminder copy.
- Production release manifest exposed matching `1.2.13` downloads for macOS arm64, macOS x64 and Windows x64.
- Post-deployment live-session count remained zero and no Web 5xx response was found in the rollout window.
