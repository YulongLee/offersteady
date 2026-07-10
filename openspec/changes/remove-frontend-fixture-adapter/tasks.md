## 1. Audit and contract mapping

- [x] 1.1 Inventory all runtime imports and references to `fixtureAdapter`, `syntheticState`, `VITE_APP_DATA_SOURCE`, fixture fallback, and synthetic page copy in `apps/web`
- [x] 1.2 Map the existing Web UI state needs for homepage, material library, interview records, user info, billing/points, Screenshot, and History
- [x] 1.3 Compare required Web state with existing Backend APIs and identify missing API fields or endpoints before frontend removal work begins

## 2. Backend API coverage

- [x] 2.1 Provide or confirm authenticated user info APIs required by the current Web UI
- [x] 2.2 Provide or confirm material library APIs for Resume, JD, Knowledge Base list/create/delete/status data
- [x] 2.3 Provide or confirm interview session and history APIs for active sessions, resumable state, conversation summaries, answers, screenshots, and deletion state
- [x] 2.4 Provide or confirm billing APIs for wallet balance, ledger entries, pricing catalog, pass state, consumption rules, and redemption code results
- [x] 2.5 Add backend contract tests that prove responses are scoped to authenticated internal User ID and do not leak cross-user data

## 3. Frontend API-only runtime

- [x] 3.1 Replace `app-adapter.ts` selection logic so product runtime always uses the Backend API adapter
- [x] 3.2 Remove `BackendPreviewInterviewAdapter` fallback dependency on `fixtureAdapter` and make missing API behavior explicit
- [x] 3.3 Remove `App.tsx` runtime initialization from `syntheticState` and replace it with API loading, empty states, and real error states
- [x] 3.4 Replace remaining user-visible actions that mutate fixture state with Backend API calls, including create/delete interview, delete screenshot, cancel answer, and redeem points
- [x] 3.5 Remove product runtime support for `VITE_APP_DATA_SOURCE=fixture` while retaining only API base URL and environment configuration

## 4. Test migration

- [x] 4.1 Create test-only API response builders or mock server helpers that are clearly separated from product runtime code
- [x] 4.2 Migrate frontend page tests currently importing `syntheticState` or `fixtureAdapter` to API mocks or test-only builders
- [x] 4.3 Update adapter tests to assert there is no probe-then-fallback behavior and that API failures surface as errors or empty states
- [x] 4.4 Add a regression test or build-time check that product runtime modules do not import `fixture-adapter`

## 5. Documentation and verification

- [x] 5.1 Update local web access and engineering docs to remove fixture runtime instructions and describe API-only startup
- [x] 5.2 Update environment documentation to remove `VITE_APP_DATA_SOURCE=fixture` as a supported product mode
- [x] 5.3 Run Web typecheck, frontend tests, relevant backend contract tests, and `openspec validate remove-frontend-fixture-adapter --strict`
- [x] 5.4 Record any backend API gaps that block complete UI data loading as follow-up Bug List or TODO List items instead of reintroducing fixture fallback
