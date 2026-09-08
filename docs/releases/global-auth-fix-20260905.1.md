# Global authentication fix 20260905.1

## Scope

- Global production Backend only.
- Adds the already approved Global email/password authentication API and its additive database migration.
- Leaves the domestic edition, Global Web/Admin containers, interviews, Companion, ASR, RAG, AI, and commerce configuration unchanged.

## Root cause

The deployed Global Web expected the password-authentication API, while the deployed Global Backend image still exposed only the legacy email-code endpoint. The browser therefore received HTTP 404 from `/api/v1/auth/global/email/send-code`.

## Release contents

- Global password registration, login, setup, reset, and change endpoints.
- Purpose-scoped email verification challenges.
- Argon2id password hashing and generic invalid-credential responses.
- Deployment-time OpenAPI contract gate for all six required authentication routes.

## Verification

- Backend authentication tests: 21 passed.
- Global Web: typecheck, 46 tests, and production build passed.
- Global Admin: 47 tests and production build passed.
- Domestic Web: typecheck and 349 tests passed.
- Backend full suite: 497 passed, 20 skipped; two unrelated realtime timing assertions were flaky in the full run and passed together in three consecutive isolated runs.
- Candidate production container: healthy, all six routes present, invalid login returns 401, malformed send-code request returns 422, and no recent application errors.

## Rollback

- Previous Backend image tag: `offersteady-global-backend:rollback-before-password-auth-fix-20260905`.
- Database backup: `/opt/offersteady-global/rollback/20260905-global-auth-fix-1/database-before-auth-fix.dump`.
- The migration is additive and remains compatible with the previous Backend image.
