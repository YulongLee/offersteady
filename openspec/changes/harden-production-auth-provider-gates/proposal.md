## Why

The production backend currently accepts an explicit `userId` when no access token is present and several AI factories silently select synthetic providers when real credentials are missing. A commercial deployment must reject unauthenticated ownership claims and fail closed instead of returning plausible but non-provider output.

## What Changes

- Require an authenticated access-token identity for every production ownership resolution.
- Keep explicit `userId` ownership only in development and test environments.
- Require real production configuration for SMS, chat, vision, realtime ASR, MinerU, embedding, and rerank factories.
- Preserve synthetic/fake adapters for local development and automated tests.
- Add regression coverage proving production rejection and development compatibility.

## Capabilities

### New Capabilities

- `production-runtime-gates`: Defines production authentication ownership and fail-closed external-provider behavior.

### Modified Capabilities

None.

## Impact

- Backend dependency factories and ownership resolution.
- Production environment configuration becomes mandatory for advertised external capabilities.
- No frontend or HTTP response-shape change; requests without production authentication now correctly return `401`.
