## Context

Global commerce already has a fail-closed checkout, signed webhook processing, versioned OfferSteady plans, and per-environment product mappings. The operator console currently reads Creem credentials only from process environment variables and exposes raw internal offer codes with free-form Product ID inputs. Creem provides isolated Test and Live API hosts and a paginated `GET /v1/products/search` endpoint, so the operator experience can use provider-owned product metadata without making that metadata authoritative for OfferSteady benefits.

## Goals / Non-Goals

**Goals:**

- Let an authorized Global administrator enter or replace Test and Live credentials without exposing saved values.
- Encrypt stored credentials with the existing server-side Admin encryption key and keep environment variables as a deployment fallback.
- Test an API key by listing Creem products and return only safe product metadata.
- Present four paid OfferSteady plans by display name, price, and billing terms and map each through a provider-product dropdown.
- Validate provider environment, active status, USD amount, and billing mode before accepting a mapping.
- Keep configuration changes fail-closed and make switching from Test to Live an operational configuration change rather than a code change.

**Non-Goals:**

- Creating, editing, or deleting Creem products from OfferSteady.
- Automatically enabling checkout after saving credentials or mappings.
- Changing prices, entitlements, webhook fulfillment, customer login, interview runtime, or the Chinese edition.
- Storing credentials in browser storage, source code, logs, or plaintext database columns.

## Decisions

### Encrypt provider credentials in the existing provider configuration row

An additive migration adds one encrypted JSON ciphertext column per Test/Live configuration. Encryption uses the existing `admin_encryption_key`-derived Fernet mechanism already used by domestic payment settings. Reads return only configured flags and non-reversible fingerprints. Environment credentials remain a fallback so existing deployments continue to work.

Alternative: mutate the server `.env` file from the browser and restart the Backend. Rejected because it grants the application filesystem/deployment authority, produces avoidable downtime, and is difficult to audit safely.

### Resolve effective credentials per provider operation

The provider factory resolves encrypted database credentials first, then environment fallback, for the explicitly requested mode. It does not retain credential values in a long-lived browser-visible object. Saving credentials invalidates readiness and disables new checkout for that environment.

Alternative: retain the current process-start singleton. Rejected because credential replacements would require a restart and a cached adapter could continue using stale secrets.

### Discover rather than create provider products

The Backend calls Creem's documented paginated product search endpoint and normalizes product ID, name, amount, currency, billing type/period, status, and mode. The Admin receives this safe catalogue and uses it for selection. Mapping still performs a fresh server-side product retrieval before persistence.

Alternative: create Creem products automatically. Rejected because the merchant already owns the provider catalogue and automatic creation risks duplicates and review inconsistencies.

### Keep Test and Live isolated

Every configuration, catalogue request, mapping, validation result, activation flag, and webhook is mode-scoped. The deployed `global_commerce_provider_mode` remains the authoritative customer-checkout environment. Operators may prepare either environment, but only the deployed environment can serve checkout. Promoting to Live requires Live credentials/products and an explicit deployment environment switch after merchant approval.

### Keep activation explicit and fail closed

Credential changes and mapping changes disable that environment. Activation requires the deployment commerce switch, configured API and webhook secrets, legal URLs, success URL, and four current validated paid-plan mappings. Test Mode can be activated for sandbox checkout; no real payment is possible because Creem isolates Test data and keys.

## Risks / Trade-offs

- [The Admin encryption key changes and stored ciphertext becomes unreadable] → Surface credentials as unconfigured and require replacement; never fall back to exposing ciphertext.
- [Creem catalogue response changes or pagination fails] → Normalize defensively, bound pagination, return a safe connection error, and leave checkout disabled.
- [A Test product is selected for Live or vice versa] → Validate the provider-reported mode against the requested environment and reject mismatches.
- [A product has the right name but wrong commercial facts] → Names are presentation only; amount, currency, billing type, status, and current OfferSteady plan version are authoritative validation gates.
- [Database configuration adds latency to checkout] → Resolve only the small provider-config row on payment operations; interview, ASR, RAG, and AI paths do not call it.

## Migration Plan

1. Apply the additive provider-credential migration on the Global database only.
2. Deploy Global Backend and Admin with checkout still disabled by provider state.
3. Configure Test credentials, copy the fixed Test webhook URL into Creem, synchronize Test products, and map the four paid plans.
4. Activate Test checkout explicitly and run success, decline, webhook, entitlement, and idempotency acceptance cases.
5. After merchant approval, create/verify Live products, configure Live credentials and webhook, switch the deployment mode to Live, revalidate, and explicitly activate Live.
6. Rollback uses the previous Backend/Admin images; the additive encrypted column and existing mappings can remain unused.

## Open Questions

None. Test Mode is the approved initial operating environment; Live remains disabled until merchant approval.
