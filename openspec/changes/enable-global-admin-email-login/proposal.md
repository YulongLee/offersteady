## Why

The Global operator console is publicly reachable at its protected hostname but still inherits the domestic phone/SMS login UI, while the Global product uses email identities. Global administration needs an email-code login path and an explicitly authorized first administrator without copying domestic identities or changing the Chinese console.

## What Changes

- Make the Global Admin build use the existing Global email verification-code APIs for login, with clear Chinese validation and recovery states consistent with the Chinese-language operator console.
- Keep the domestic Admin build on its existing Chinese phone/SMS login path.
- Bootstrap the operator-approved email identity as the first Global super administrator in the isolated Global database through an audited server-side operation; do not hardcode that identity or any verification code in client source or change artifacts.
- Keep administrator session creation, permissions, rate limits, and audit behavior unchanged after the user access token is issued.
- Verify the public Global Admin hostname, unauthenticated protection, email delivery, administrator session, and domestic production isolation before acceptance.

## Capabilities

### New Capabilities

- `global-admin-email-login`: Email-code authentication and explicit first-administrator authorization for the independently deployed Global operator console.

### Modified Capabilities

None.

## Impact

- Affects the edition-aware login surface and API client in `apps/admin`, Global Admin build tests/configuration, overseas deployment configuration, and Global administrator authorization data.
- Reuses the existing server-side email provider and authentication endpoints; no new credential is introduced and no email code is logged or stored in client code.
- Does not change the Chinese Admin UI, domestic SMS authentication, customer-facing Global Web, interview processing, billing activation, or either production database outside the isolated Global administrator authorization row.
