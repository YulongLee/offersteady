## Why

The Global operator console currently exposes several China-only commercial modules, including domestic payment channels, points products, redemption codes, referrals, and the domestic promotion centre. These entries are unusable or misleading for the independent OfferSteady international product, whose commercial operations are owned by the Creem-specific module.

## What Changes

- Limit the Global Admin navigation to dashboard, server health, users, Global Creem commerce, materials, interview sessions, audit records, and administrator access.
- Remove China-only promotion, domestic orders/payment diagnostics, WeChat/Alipay settings, referral growth, points catalogue, and redemption-code entries from the Global Admin build.
- Keep the Chinese Admin build and all shared Backend APIs unchanged.
- Add regression coverage proving the edition-specific menu boundary and valid fallback navigation.

## Capabilities

### New Capabilities

- `global-admin-module-scope`: Defines the management modules visible in the independent Global operator console and its isolation from China-only operations.

### Modified Capabilities

None.

## Impact

- Affected UI: `apps/admin` navigation and view selection.
- Affected deployment: only the `VITE_PRODUCT_EDITION=global` Admin bundle on `admin.offersteady.com`.
- No Backend route, database schema, customer Web, Companion, ASR, RAG, AI, billing state, or Chinese production behavior changes.
