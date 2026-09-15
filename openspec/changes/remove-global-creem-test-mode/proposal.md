## Why

The international admin console currently exposes Creem Test and Live environments even though the business has completed approval and wants to operate only the formal payment environment. The extra test mode causes operators to select or save the wrong environment and leaves the console showing a misleading “test” state.

## What Changes

- Remove Test environment controls and Test-only status text from the international payment administration UI.
- Make the international payment configuration and activation flow use Live credentials, Live products, Live mappings, and the Live webhook only.
- Prevent Test-mode payment configuration endpoints from being used by the international admin flow, while preserving existing orders and webhook idempotency.
- Keep domestic payment behavior and the public international checkout flow unchanged except for selecting the validated Live provider.
- **BREAKING**: International administrators will no longer be able to configure or activate Creem Test mode from the console.

## Capabilities

### New Capabilities
- `global-live-only-commerce`: International Creem administration and checkout operate exclusively against the validated Live environment.

### Modified Capabilities

## Impact

- Affected code: international admin payment panel, global commerce admin APIs/configuration service, provider selection and related tests.
- Existing Test credentials/mappings remain data that may need migration or deactivation; no customer orders or entitlement records should be deleted.
- Deployment configuration must provide Live API Key, Live Webhook Secret, production public URLs, and the global commerce master switch.
