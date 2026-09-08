## Why

OfferSteady needs an English product for the United States, United Kingdom, Australia, and Canada without putting the validated Chinese production experience at risk. The international experience must therefore be independently buildable and deployable while retaining functional parity with the current end-user product.

## What Changes

- Add an independently runnable and buildable Global English web application covering the current public, authentication, preparation, interview, written-exam, material, billing, device, settings, legal, and help journeys.
- Add an international desktop-companion presentation/build profile so end-user companion labels, guidance, and update metadata can be English without changing the Chinese release profile.
- Reuse shared protocols and stable runtime behavior while isolating Global public configuration, branding, locale, release artifacts, and future deployment values from the Chinese application.
- Keep the operator/admin application in Chinese.
- Route Global interview, screenshot, programming, and continuation behavior through the existing English prompt assets and enforce English output for Global sessions.
- Add regional locale profiles for `en-US`, `en-GB`, `en-AU`, and `en-CA`, with English as the only user-facing language in this release.
- Add regression checks proving that Global builds contain the expected English experience and that the existing Chinese build and its production configuration remain unchanged.
- Defer international server provisioning, production domain setup, payment-provider activation, legal approval, and production deployment until the operator supplies the required infrastructure and commercial configuration.

## Capabilities

### New Capabilities

- `independent-global-english-product`: Independently built Global English web and companion experiences with feature parity, English AI behavior, regional locale profiles, and release/configuration isolation from the Chinese product.

### Modified Capabilities

<!-- No existing capability requirement changes. The Chinese product remains behaviorally unchanged. -->

## Impact

- Adds a new end-user application/build boundary under `apps/` and shared locale/brand configuration where appropriate.
- Updates workspace scripts, build validation, English prompt/eval coverage, and documentation for independent Global builds.
- May add an international build profile to `apps/desktop`; the existing Chinese desktop profile and artifacts remain unchanged.
- Reuses the current backend API contract during local development. A later deployment will use independent server, database, cache, object storage, AI credentials, monitoring, domain, and payment configuration.
- No production deployment, database migration, live secret change, or modification to `apps/admin` is included.
