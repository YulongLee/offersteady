## Why

The Global customer product currently requires an emailed one-time code for every sign-in. This is slower and less familiar than email-and-password authentication for repeat users, and it makes routine access depend on email delivery.

## What Changes

- Replace the Global customer sign-in default with email and password.
- Add a verified registration journey: email verification code followed by password creation.
- Add authenticated password change and email-verified forgotten-password recovery.
- Migrate existing passwordless Global customer accounts safely by allowing email verification to establish their first password.
- Add password hashing, credential throttling, one-time recovery challenges, session revocation, and security audit events appropriate for a commercial service.
- Keep domestic phone/SMS authentication, the domestic Web, and Global Admin authentication unchanged.

## Capabilities

### New Capabilities

- `global-password-authentication`: Global customer registration, password sign-in, initial-password migration, password change, and password recovery with verified email ownership and abuse controls.

### Modified Capabilities

None. The existing email-code capability remains the verified-email primitive, while this change introduces the Global-only password lifecycle that consumes it.

## Impact

- Adds Global customer authentication schemas and API routes, password/recovery service behavior, persistent recovery purpose/state, and regression tests.
- Updates only `apps/web-global` authentication and account-security UI; domestic `apps/web`, phone/SMS endpoints, and Global Admin login remain unchanged.
- Requires an additive Global database migration and production environment configuration. Existing users, sessions, billing, materials, and interview data remain attached to their current user IDs.
- Passwords and raw verification codes are never logged or stored in plaintext.
