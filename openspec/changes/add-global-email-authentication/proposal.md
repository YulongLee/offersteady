## Why

The Global product currently inherits a China-oriented phone/SMS authentication journey that is unsuitable for users in the United States, United Kingdom, Australia, and Canada. Global accounts need an email-first registration and sign-in flow while the validated Chinese phone flow remains unchanged.

## What Changes

- Add email verification-code registration and sign-in endpoints backed by persistent, one-time, expiring challenges.
- Add a replaceable server-side email delivery adapter with a production fail-closed configuration and non-production test mode.
- Make the Global Web authentication journey email-only and English, including validation, resend timing, loading, expiry, and failure states.
- Keep the Chinese Web and domestic phone/SMS authentication APIs and behavior unchanged.
- Keep Global and domestic users, challenges, sessions, secrets, rate limits, and provider configuration isolated.
- Do not deploy or activate production email delivery until the operator supplies and verifies an approved provider account and sending domain.

## Capabilities

### New Capabilities

- `global-email-authentication`: Verified email registration and sign-in for the independently deployed Global product, with persistent challenges, abuse controls, provider isolation, and English UI behavior.

### Modified Capabilities

None. The Global-only behavior and production activation gate are specified by the new capability without changing the domestic product specifications.

## Impact

- Adds Backend email-auth API schemas, repository persistence, delivery adapter, settings, migrations, and regression tests.
- Updates only `apps/web-global` authentication UI/client behavior; `apps/web`, domestic SMS endpoints, and the Chinese Admin remain unchanged.
- Adds server-only email provider variables and operational documentation. No provider credentials are committed or printed.
- Requires an additive Global database migration and a separately configured production email provider before deployment.
