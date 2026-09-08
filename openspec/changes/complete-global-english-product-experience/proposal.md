## Why

The Global product currently relies on broad fallback translations inherited from the Chinese application, so multiple routes show repeated, contextually incorrect English, mixed Chinese/English text, and layouts that break under longer labels. Before international launch, the complete customer-facing journey needs explicit English copy and responsive presentation, while Global commerce and growth behavior must reflect the international product rather than exposing domestic payment or referral flows.

## What Changes

- Replace generic build-time translation fallbacks across all supported Global customer routes with explicit, context-appropriate English product copy.
- Make missing product-copy translations a build failure while preserving user-provided or server-provided content exactly as received.
- Review and correct responsive layout, hierarchy, labels, empty states, errors, and actions across public, authentication, interview, written-exam, material, device, settings, help, and account surfaces.
- **BREAKING** Remove the invitation/referral campaign experience from the Global product, including its navigation, landing route, referral cards, and automatic referral API requests. Legacy Global invitation URLs safely return users to the public entry flow without activating a referral.
- Replace the Global billing surface with an international commerce boundary that shows existing credits, entitlements, usage rules, and ledger history in English without exposing Alipay, WeChat Pay, QR checkout, or domestic catalogues.
- Reserve checkout for a later Creem integration. This change does not create a fake checkout, enable payments without configured products and secrets, or alter the Chinese payment system.
- Keep the Chinese Web, Chinese admin, domestic payment/referral behavior, backend interview APIs, and desktop companion behavior unchanged.

## Capabilities

### New Capabilities

- `global-copy-completeness`: Explicit, context-appropriate English copy across every supported Global customer route, with build-time completeness enforcement and preservation of user content.
- `global-responsive-feature-pages`: Readable and usable Global feature pages across desktop, tablet, and mobile using the existing dark-and-green design system.
- `global-commerce-boundary`: Global-only removal of referral behavior and a safe international billing boundary prepared for a future server-side Creem integration.

### Modified Capabilities

<!-- No main-spec capability requirements change. The Chinese product remains behaviorally unchanged. -->

## Impact

- Primarily affects `apps/web-global`, its copy catalogue/generator, Global route definitions, Global billing presentation, styles, and route-level tests.
- May add Global-only public runtime configuration for a future commerce provider, but no Creem secret or payment decision is stored in the browser.
- Does not migrate data, alter current credit balances, persist additional interview/audio/screenshot data, or change the Chinese application and administration surfaces.
- Global deployment must remain independently reversible to the current `offersteady.com` baseline.
