## 1. Session contract and persistence

- [x] 1.1 Add closed programming-language types, request/response fields, validation, and backward-compatible defaults.
- [x] 1.2 Add a forward-only database migration and update in-memory/PostgreSQL repositories for programming preference round trips.
- [x] 1.3 Add an owner-only preparing-state update command/API and preserve the preference when restarting a session.

## 2. Preparation experience

- [x] 2.1 Extend Web domain types and Backend Adapter mapping/update support.
- [x] 2.2 Add the optional programming switch and conditional language selector to the existing preparation layout without adding a readiness gate.
- [x] 2.3 Add Web tests for defaults, save/restore, supported languages, disabling, and save failures.

## 3. Answer routing

- [x] 3.1 Add centralized Chinese and English programming-policy Prompt assets and a closed-enum renderer.
- [x] 3.2 Inject the authoritative policy into Chat quick/detail/continuation and legacy answer paths.
- [x] 3.3 Inject the authoritative policy into screenshot visual-direct and composed answer paths.

## 4. Verification

- [x] 4.1 Add backend contract, ownership, state-lock, persistence, restart, and Prompt regression tests.
- [x] 4.2 Add synthetic AI eval cases for all supported languages, non-coding questions, English interviews, and screenshot coding questions.
- [x] 4.3 Run focused and full backend/Web tests, typecheck/build, strict OpenSpec validation, and inspect the final diff for sensitive-data regressions.
