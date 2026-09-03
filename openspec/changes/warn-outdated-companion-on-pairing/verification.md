# Verification

## Pre-deployment

- Focused tests: `npm run test -w @offersteady/web -- --run src/App.test.tsx src/platform.test.ts` — 40 passed.
- Full Web suite: `npm run test -w @offersteady/web` — 47 files, 349 tests passed.
- Production build: `VITE_APP_ENV=production VITE_API_BASE_URL=/ VITE_PUBLIC_APP_VERSION=0.1.0 npm run build -w @offersteady/web` — passed.
- Spec validation: `openspec validate warn-outdated-companion-on-pairing --strict` — passed.
- Diff hygiene: `git diff --check` — passed.

## Production deployment

Pending active-interview gate and Web-only rollout.
