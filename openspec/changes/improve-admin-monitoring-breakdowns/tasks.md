## 1. Backend request classification

- [x] 1.1 Add privacy-safe route normalization and stable request classes to the bounded request window.
- [x] 1.2 Add rolling class summaries and capped slow-route diagnostics while preserving legacy aggregate fields.
- [x] 1.3 Add backend tests for classification, redaction, ordering, caps, and empty-window behavior.

## 2. Admin response and dashboard

- [x] 2.1 Serialize the request breakdown in the existing admin capacity response with backward-compatible defaults.
- [x] 2.2 Render a compact breakdown panel in the existing dashboard style without changing layout or user-facing interview flows.
- [x] 2.3 Add frontend tests for new data and older-backend fallback behavior.

## 3. Verification

- [x] 3.1 Run focused backend/frontend tests, typecheck, production build, and strict OpenSpec validation.
- [x] 3.2 Review the diff for sensitive fields, verify no new persistence or provider changes, and prepare a release note for a later deployment.
