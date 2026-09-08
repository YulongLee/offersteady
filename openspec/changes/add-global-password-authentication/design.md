## Context

The Global customer Web currently sends a one-time email code for both first registration and every later sign-in. Verified email users are stored in the isolated Global database with their normalized email as `login_id`, an `email` identity binding, and `external-auth` in the required password field. The Backend already issues rotating access/refresh sessions and contains a legacy PBKDF2 password path, but its current work factor and domestic-facing API contract are not an appropriate Global password baseline.

This change crosses Global Web, Backend authentication, PostgreSQL migrations, email delivery, and existing-account migration. Domestic SMS login and Global Admin email-code login are separate product surfaces and must not change.

## Goals / Non-Goals

**Goals:**

- Make email and password the default repeat-login experience for Global customers.
- Verify mailbox ownership before creating a password-backed account.
- Let existing passwordless Global customers establish a password without changing user IDs or losing data.
- Provide distinct authenticated password-change and forgotten-password recovery journeys.
- Apply commercial abuse, password-storage, session-revocation, and account-enumeration protections.

**Non-Goals:**

- Changing domestic phone/SMS login, domestic Web, or Global Admin authentication.
- Adding social login, passkeys, MFA, email-address changes, or account merging in this change.
- Copying accounts between domestic and Global databases.
- Deploying automatically before the migration and Global smoke tests pass.

## Decisions

### Gate all new password behavior to the Global product edition

New registration, password login, recovery, and change endpoints will reject requests unless `product_edition == "global"` and Global email authentication is enabled. Only `apps/web-global` calls them. Existing generic register/login and domestic SMS routes remain behaviorally unchanged.

Alternative considered: replace the shared generic password endpoints. That risks exposing an unverified registration path and altering domestic behavior.

### Use purpose-bound email challenges

Email challenges gain an additive purpose field: `login`, `registration`, `password_setup`, or `password_reset`. Registration and recovery completions only accept matching, unexpired, unused challenges. A code issued for one purpose cannot be replayed for another.

Alternative considered: reuse the current undifferentiated challenge. That allows cross-flow replay and makes security auditing ambiguous.

### Use Argon2id for new Global passwords and retain legacy verification compatibility

New and changed Global passwords are hashed with Argon2id using versioned encoded hashes and a server-tuned bounded work factor. The verifier retains compatibility with existing PBKDF2 hashes and rehashes them after a successful login when policy requires it. Placeholder values such as `external-auth` never authenticate.

Alternative considered: keep PBKDF2 at the existing 120,000 iterations. It is below the intended commercial password-storage baseline and provides no memory-hard resistance.

### Make registration and existing-user setup explicit

Registration sends a `registration` code and completes with email, code, and password. It fails generically when the email is already registered. Existing passwordless users use a `password_setup` flow that verifies the same mailbox, writes a password hash to the existing user row, and retains the user ID, billing, materials, and sessions.

The legacy email-code login endpoint remains temporarily available for migration compatibility, but the Global UI no longer presents it as the default login.

Alternative considered: silently treat every verified code as both registration and password reset. That creates account-discovery and accidental credential replacement risks.

### Separate change-password from forgotten-password recovery

An authenticated password change requires the current password and new password, then revokes other active sessions. Forgotten-password recovery requires a purpose-bound email code, installs a new password, consumes the challenge, and revokes all prior sessions before issuing a fresh session.

Alternative considered: email verification for every authenticated password change. This adds unnecessary email dependency and weakens the meaning of possession of the current credential.

### Enforce usability-oriented password policy and generic failures

Passwords allow spaces, Unicode, paste, autofill, and at least 64 characters. A single-factor password requires at least 15 characters and is checked against a bundled common-password blocklist. Login and recovery responses use generic account messages, and attempts are throttled by normalized account and request origin without logging passwords, codes, or full recovery data.

Alternative considered: composition rules such as mandatory uppercase, number, and symbol. These increase friction without providing the same protection as length, blocklisting, and throttling.

## Risks / Trade-offs

- [Existing email-code users cannot password-login immediately] → Keep the setup-by-email path and temporary legacy email-code API compatibility; never create a second account.
- [Credential stuffing and brute force] → Apply account/IP throttling, generic errors, common-password rejection, secure hashing, and security audit events.
- [Password hashing increases CPU load] → Benchmark the Argon2id parameters on the overseas host and cap concurrent unauthenticated attempts; do not weaken interview runtime workers.
- [Recovery email is delayed] → Keep resend/expiry feedback, make reset codes one-time, and avoid revealing whether the address exists.
- [Recovery takes over an account] → Bind challenge purpose and address, enforce expiry/attempt limits, revoke old sessions, and send a password-change notice.
- [Shared authentication files affect domestic behavior] → Gate service methods and routes by product edition and add explicit domestic non-regression tests.

## Migration Plan

1. Add the purpose column and indexes as an additive migration; deploy Backend support without changing the Global UI.
2. Run Backend service/API tests, migration tests, domestic authentication regression tests, and Global Web tests.
3. Verify registration, existing-user password setup, login, forgotten password, password change, session revocation, and generic failure behavior against an isolated Global database.
4. Deploy the Global Backend, run a health check, then deploy `apps/web-global` with password login as the default.
5. Monitor login failures, email delivery, hash latency, and recovery attempts without recording secrets.

Rollback restores the previous Global Web and Backend image. The additive purpose column remains harmless, and existing users can continue through the legacy email-code endpoint. No user row or session is deleted during schema migration.

## Open Questions

- How long should the legacy Global email-code login endpoint remain available after all active users have been offered password setup?
