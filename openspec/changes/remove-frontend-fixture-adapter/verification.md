# Verification and follow-up gaps

## Completed verification

- Frontend runtime modules now instantiate the Backend API adapter directly.
- Web app initialization loads `/api/v1/web/state` and shows loading/error states instead of initializing from `syntheticState`.
- Product runtime no longer supports `VITE_APP_DATA_SOURCE=fixture` or probe-then-fallback behavior.
- Test data has been isolated to test-only helpers:
  - `apps/web/src/test-state.ts`
  - `apps/web/src/test-adapter-builders.ts`
- A frontend regression test checks that product runtime modules do not import `fixture-adapter` or `syntheticState`.
- Backend contract coverage includes `/api/v1/web/state` authenticated user scoping and cross-user leakage checks.

## Follow-up TODOs

- Material collection rename/delete are still local UI transformations because a dedicated collection-management API is not yet available. Do not reintroduce fixture fallback for this; add real collection update/delete endpoints in a future Document/Knowledge management change.
- Manual live answer and screenshot prototype interactions still create optimistic UI entries before full streaming orchestration is wired into the Web page. They must be replaced by Chat/Screenshot API flows in the full E2E integration work, not by local fixture state.
- Local development now needs backend seed/dev data or a real test account to display populated product pages. Empty or error pages are expected if the backend has no state for the logged-in user.
