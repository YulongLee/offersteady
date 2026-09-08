## Context

The Global customer application already has production email-code authentication backed by the isolated Global database and SMTP configuration. The shared Admin source currently renders a phone/SMS login for every build, although its Admin session endpoint accepts any valid first-party user access token and then checks the separate `admin_authorizations` table. The Global Admin hostname and API are now protected and reachable, but there are no Global administrator authorizations.

The Chinese Admin must retain its current phone/SMS flow. Email addresses and verification codes are authentication data: raw codes and provider secrets must never enter browser constants, source control, logs, or test fixtures.

## Goals / Non-Goals

**Goals:**

- Build an email-code login UI only when `VITE_PRODUCT_EDITION=global`.
- Reuse the existing email send/verify endpoints, then exchange the returned user token through the unchanged Admin session endpoint.
- Bootstrap the explicitly approved email identity as the first Global super administrator through a one-time server-side operation.
- Keep the Global and domestic builds, users, authorization rows, secrets, and deployment processes isolated.

**Non-Goals:**

- Changing domestic Admin login, domestic administrator data, or customer-facing Global authentication.
- Hardcoding an administrator email, verification code, access token, or privilege bypass into client or server source.
- Adding passwords, social login, or a second administrator-management model.

## Decisions

### Select the Admin login method at build time

The shared Admin application will read the existing public `VITE_PRODUCT_EDITION` build flag. The Global build renders email fields and calls email authentication endpoints; the domestic build preserves the current phone UI and SMS calls. This keeps common dashboard code shared without runtime hostname guessing.

Alternative considered: create a full `apps/admin-global` fork. That would duplicate a large operational console and cause security and feature drift.

### Reuse the existing verified-email token exchange

The Admin client will add typed email send and verify methods mirroring the Global customer flow. After email verification returns a normal access token, the client calls the unchanged `/api/v1/admin/session` endpoint. Authorization therefore remains server-side and an unapproved email still cannot enter the console.

Alternative considered: add a separate Admin email endpoint. That would duplicate challenge security and session issuance without adding a security boundary.

### Store the approved administrator only in Global authorization data

The first administrator is created with `AdminService.bootstrap()` against an already verified Global email user. The approved address is supplied to the one-time server command, not committed. The bootstrap output includes a TOTP enrollment secret; it must be delivered only through the protected operator session and never written to logs or release documentation. If the email user does not yet exist, the operator must complete email verification first.

Alternative considered: an environment-variable allowlist. This would make possession of an email account implicitly grant persistent administrator rights and would weaken explicit revocation/audit semantics.

### Deploy Global Admin independently

Only the Global Admin image is rebuilt for the UI change. Backend code is unchanged. Production verification covers the email endpoints, protected Admin session endpoint, Global health, and domestic health. The prior Global Admin image is retained for rollback.

## Risks / Trade-offs

- [Edition flag is missing during build] → Default to the existing domestic phone flow and require the Global Docker build to set `VITE_PRODUCT_EDITION=global`.
- [Approved email has no Global user yet] → Complete one email verification before bootstrap; never create an unverified identity directly.
- [Email delivery is delayed] → Preserve cooldown, masked destination, retry, and error handling from the existing Global email flow.
- [Shared Admin changes regress domestic login] → Add explicit tests for both edition profiles and run the existing Admin suite/build before deployment.
- [First-admin bootstrap leaks TOTP material] → Do not print or persist the secret in task output, logs, or documentation; record only authorization status.

## Migration Plan

1. Add edition-aware Admin client methods, UI, and tests.
2. Run Admin tests, typecheck/build for domestic and Global build profiles, Backend authentication/Admin regressions, and strict OpenSpec validation.
3. Retain the current Global Admin image and deploy only the rebuilt Global Admin service.
4. Have the approved email complete Global email verification if its isolated user does not yet exist.
5. Bootstrap that Global user as `super_admin`, verify the authorization count and protected session behavior, and avoid exposing secret material.
6. Verify Global and domestic health. Roll back only the Global Admin image if the UI regresses; authorization data remains explicit and auditable.

## Open Questions

None. The Global login method, first administrator identity, and domestic isolation boundary are explicitly approved.
