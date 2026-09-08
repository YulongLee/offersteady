## Why

The current Global Admin exposes internal OfferSteady offer codes and requires operators to paste Creem Product IDs, while credentials can only be injected through server environment variables. This makes Creem Test Mode difficult to configure and validate and makes the page look as if internal plans were provider products.

## What Changes

- Add a safe Global Admin configuration flow for separate Creem Test and Live credentials, with encrypted server-side storage and masked readback.
- Add an explicit connection check and server-side retrieval of the current environment's Creem products.
- Replace raw Product ID entry with human-readable OfferSteady plan cards and a Creem product selector that validates price, currency, billing type, status, and environment.
- Keep Test and Live credentials, products, mappings, activation, and acceptance state isolated.
- Keep checkout disabled after sensitive configuration changes and until every paid plan passes validation; Free remains outside Creem mapping.
- Preserve the existing Global checkout, webhook, entitlement, login, interview, Companion, ASR, RAG, AI, API, and Chinese-edition behavior.

## Capabilities

### New Capabilities

- `global-creem-test-operations`: Safe operator configuration, provider catalogue discovery, readable plan mapping, and Test-to-Live isolation for Global Creem commerce.

### Modified Capabilities

None.

## Impact

- Global-only Admin UI and Admin API endpoints.
- Global Backend Creem adapter, configuration service, repository, and an additive database migration.
- Global commerce regression tests, Admin component/client tests, deployment documentation, and OpenSpec validation.
- No changes to Chinese production routes or customer-facing interview runtime.
