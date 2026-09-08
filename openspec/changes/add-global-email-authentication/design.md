## Context

The independently deployed Global product currently reuses the domestic phone/SMS authentication API and presents that journey through an English translation layer. Email is the expected account identifier for the initial United States, United Kingdom, Australia, and Canada launch. Authentication spans the Global Web, Backend service, PostgreSQL schema, provider configuration, and deployment runbook. The domestic Web and its validated Aliyun SMS journey must remain unchanged.

Email addresses and verification codes are sensitive authentication data. Provider secrets must remain server-side, verification codes must not be logged or stored in plaintext, and production must not silently fall back to a development sender.

## Goals / Non-Goals

**Goals:**

- Provide one English email-code journey that registers a new user or signs in an existing verified user.
- Persist one-time, expiring verification challenges and enforce resend and attempt limits.
- Keep email delivery behind a replaceable server-side provider port, with a generic SMTP implementation and a deterministic test implementation.
- Scope all Web changes to `apps/web-global` and preserve domestic SMS behavior.
- Fail closed when Global email authentication is enabled in production without a valid provider configuration.

**Non-Goals:**

- Password reset, magic links, social login, account merging, or changing the Chinese Admin authentication journey.
- Selecting or purchasing an email provider on the operator's behalf.
- Activating production email login before sender-domain verification and end-to-end deliverability checks are complete.
- Migrating domestic users or copying user data between domestic and Global databases.

## Decisions

### Use a single email verification-code flow for registration and sign-in

The Backend will create an account after the first successful verification and issue a normal auth session for later successful verifications. This removes a redundant registration/sign-in choice and proves mailbox control before account creation.

Alternative considered: email and password registration. This adds password reset, breach handling, password policy, and more UI states without improving the first-launch journey.

### Add an email provider port with SMTP and fake implementations

The service layer will depend on an `EmailVerificationProviderPort`. SMTP gives the deployment a provider-neutral commercial path; a fake adapter is allowed only outside production for deterministic tests. Provider credentials and the code-signing pepper are server settings.

Alternative considered: integrate one vendor SDK directly. That would make the UI and service behavior depend on a vendor and complicate a later provider change.

### Reuse the existing OneShow SMTP transport for the initial Global release

The initial Global deployment reuses the SMTP host, port, mailbox credentials, and sender address already operated by OneShow. Those values are copied only between server-side environment files and are never committed or printed. OfferSteady keeps its own verification-code HMAC pepper, email challenge records, rate limits, and provider adapter, so sharing the delivery transport does not merge authentication state or user data between products. The sender display name remains `OfferSteady`.

Alternative considered: block launch until a dedicated `offersteady.com` sender is provisioned. A dedicated sender remains preferable for long-term reputation isolation, but it is not required to validate the email authentication product flow and can replace the SMTP settings without changing application code.

### Persist only the authentication data needed for verification

Challenges will persist a normalized email hash, masked destination, status, expiry, attempt count, provider references, and an HMAC digest of the code. The verified account necessarily stores the normalized email as its login identifier. Raw codes are never persisted or logged.

Alternative considered: store the full email and plaintext code in the challenge table. This simplifies debugging but creates unnecessary credential and privacy exposure.

### Reuse existing session and user primitives

After successful verification, email users receive the same access/refresh token pair and session lifecycle as SMS users. The identity binding gains an `email` provider kind. This keeps authorization behavior consistent while the Global database remains physically isolated.

Alternative considered: build a separate Global session subsystem. That duplicates security-critical logic and increases rollout risk without a product benefit.

### Keep domestic behavior unchanged through opt-in configuration and app scoping

Email endpoints will be disabled unless `OFFERSTEADY_AUTH_EMAIL_ENABLED` is true. Only `apps/web-global` will call them. Existing SMS endpoints, domestic Web source, and Chinese Admin remain unchanged. Global production activation will be a configuration-only step after provider readiness.

Alternative considered: replace the existing SMS endpoints. That would create an unnecessary domestic regression risk and violate deployment isolation.

## Risks / Trade-offs

- [Email delivery is delayed or filtered] -> Verify SPF, DKIM, and DMARC; use a transactional sender; monitor provider response IDs and delivery metrics without logging full addresses.
- [Verification endpoint is abused] -> Enforce per-address resend interval, daily send limit, challenge expiry, attempt cap, generic errors, and provider-side quotas.
- [Provider is missing or misconfigured] -> Production startup/configuration fails closed when email is enabled; the existing deployed release stays active until a smoke test succeeds.
- [Concurrent verification creates duplicate accounts] -> Normalize addresses, retain the unique login identifier constraint, and make get-or-create resilient to the unique-key race.
- [Email aliases or case rules differ by provider] -> Lowercase the domain and the whole address for initial consistency; do not strip plus addressing or alter dots.
- [Shared SMTP reputation or quota affects both products] -> Monitor delivery failures and provider quotas, keep product-specific authentication metrics, and migrate OfferSteady to a dedicated sending domain when volume justifies isolation.

## Migration Plan

1. Add the email challenge schema as an additive migration and deploy code with email authentication disabled.
2. Run Backend unit/API tests and Global Web tests using the fake provider in the test environment.
3. Configure a verified sender, SMTP credentials, code pepper, and Global-only email settings on the overseas server.
4. Apply the migration to the isolated Global database, enable email authentication, and verify send, invalid-code, expiry, successful registration, repeat sign-in, refresh, and logout.
5. Deploy the email-only Global Web after Backend verification succeeds; retain the prior Global image tags for immediate rollback.
6. Confirm domestic SMS login and domestic production health are unchanged.

Rollback restores the previous Global Web and Backend images. The additive challenge table can remain unused; no destructive database rollback is required.

## Open Questions

- When should the Global product move from the shared OneShow SMTP transport to a dedicated `offersteady.com` sending domain?
