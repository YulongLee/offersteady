## 1. Baseline and regression coverage

- [x] 1.1 Record the active Global Admin/Web/Backend releases, administrator count, public route status, and rollback images without exposing secrets
- [x] 1.2 Add synthetic regression tests for Global email login, unauthorized email behavior, and unchanged domestic phone login

## 2. Edition-aware Admin authentication

- [x] 2.1 Add typed Admin client methods for the existing email send-code and verify-login endpoints
- [x] 2.2 Render email validation, send, cooldown, verification, and error states only in the Global Admin build
- [x] 2.3 Preserve the domestic phone/SMS UI and API behavior when the Global edition flag is absent

## 3. Verification

- [x] 3.1 Run focused and full Admin tests, typecheck, domestic build, Global build, and relevant Backend auth/Admin regressions
- [x] 3.2 Run strict OpenSpec validation and verify no administrator identity or authentication secret is committed or printed

## 4. Global deployment and authorization

- [x] 4.1 Confirm zero active Global interviews, retain the current Global Admin image, and deploy only the Global Admin image
- [x] 4.2 Verify the approved email through the existing Global email flow if its isolated user does not already exist
- [x] 4.3 Bootstrap the approved Global user as the first super administrator without exposing enrollment secret material
- [ ] 4.4 Verify HTTPS, security headers, anonymous HTTP 401, successful authorized login, Global health, domestic health, and rollback readiness
