# Global authentication purpose fix 20260905.2

## Scope

- Global production Backend and Global Web only.
- Domestic services, Global Admin, interviews, Companion, ASR, RAG, AI, billing, PostgreSQL, and Redis are unchanged.

## Fix

- Preserve the purpose stored with PostgreSQL email challenges when records are read back.
- Registration, initial password setup, and password reset can now consume their matching purpose-bound verification challenges.
- Show an actionable request-new-code message for a genuinely unavailable verification session instead of the generic not-found copy.

## Verification

- Authentication Backend tests: 19 passed.
- Global Web tests: 47 passed.
- Global Web typecheck and production build passed.
- Domestic Web typecheck and 349 tests passed.
- The unrelated realtime prewarm timing assertion that fluctuated in the full Backend run passed three consecutive isolated runs.
- OpenSpec strict validation passed.

## Rollback

Rollback uses the Backend and Web images tagged before this release. This release has no database migration and does not mutate existing users or verification challenges during deployment.
