## Context

OfferSteady has separate adapters for local synthetic behavior and real commercial providers. Repository persistence already fails closed in production, but provider factories do not consistently apply the same rule. Ownership resolution also retains a prototype compatibility path that trusts an explicit user identifier without authentication.

## Goals

- Prevent unauthenticated account impersonation in production.
- Prevent synthetic model, speech, parsing, embedding, rerank, or SMS behavior from being selected in production.
- Keep local tests deterministic and credential-free.
- Avoid logging or returning secret values during configuration validation.

## Non-Goals

- Migrating billing orders and entitlements to PostgreSQL; that remains the next isolated commercial hardening change.
- Changing access-token format or browser token storage.
- Calling providers during application startup.

## Decisions

### Ownership is environment-aware

`resolve_owned_user_id` continues to accept explicit identities only outside production. Production requests without an authenticated context receive `401`, and a conflicting explicit identity continues to receive `403`.

### Provider factories validate required fields

A shared helper validates only whether required server-side values are present. Error messages contain capability and environment-variable names but never secret values. Each production factory validates before selecting its real adapter.

### Development compatibility remains explicit

Development and tests retain fake SMS and synthetic AI adapters. This keeps deterministic test behavior without weakening production.

## Risks

- Missing production variables will make an affected feature unavailable instead of degraded. This is intentional; deployment preflight checks must detect missing variables before rollout.
- Existing unauthenticated prototype clients will receive `401` in production and must authenticate normally.

## Verification

- Unit tests cover production ownership denial and every provider factory.
- Existing backend regression tests run with deterministic local adapters.
- Deployment preflight checks variable presence without printing values.
- OpenSpec strict validation passes.
