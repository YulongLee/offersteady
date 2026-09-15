## 1. Backend mode enforcement

- [x] 1.1 Centralize global Creem mode resolution to Live and reject explicit Test-mode admin requests.
- [x] 1.2 Update global readiness and activation checks to validate only Live credentials, webhook secret, URLs, and mappings.
- [x] 1.3 Ensure global checkout and webhook provider construction cannot fall back to Test mode.

## 2. Admin interface

- [x] 2.1 Remove the Test/Live selector and render a single Live payment configuration panel for the global edition.
- [x] 2.2 Update global admin API client calls and status copy to use Live-only endpoints and terminology.
- [x] 2.3 Preserve masked secrets, mapping controls, audit visibility, and clear incomplete-Live setup errors.

## 3. Verification and rollout

- [x] 3.1 Add backend regression tests for Test-mode rejection, Live readiness, and domestic-edition isolation.
- [x] 3.2 Update admin component/API tests to assert Test controls are absent and Live controls remain usable.
- [x] 3.3 Run backend/frontend typecheck, lint, unit tests, and OpenSpec validation; document required Live environment variables and rollback steps.
