## ADDED Requirements

### Requirement: Checkout creates a server-priced official payment order
The checkout SHALL submit only the selected published SKU and payment channel. The server SHALL snapshot the product, amount, currency and owner, then create a WeChat Pay or Alipay order through a server-only provider adapter.

#### Scenario: User starts checkout
- **WHEN** an authenticated user selects a product and official channel
- **THEN** the server returns an order number, authoritative amount, expiry and provider checkout action without trusting a client price

### Requirement: Payment interaction uses a dynamic provider action
WeChat Native and supported Alipay modes SHALL return a short-lived order-specific QR value or official checkout redirect. The UI SHALL show order, amount, channel, expiry and current status. It MUST NOT request a transaction number, payment screenshot or payer identity.

#### Scenario: User chooses desktop WeChat Pay
- **WHEN** the provider successfully creates a Native payment
- **THEN** the checkout renders a dynamic order QR and polls only the OfferSteady order status

#### Scenario: Provider order creation fails
- **WHEN** the provider cannot create a payment action
- **THEN** the order remains unpaid, no entitlement is issued and the user can safely retry or choose another channel

### Requirement: Only verified server payment evidence can activate entitlement
The system MUST verify provider notification signatures, merchant identity, application identity, order number, amount and payment state. A successful verified notification or active server query SHALL activate entitlement exactly once in the same transactional boundary.

#### Scenario: Verified notification is replayed
- **WHEN** the same valid paid notification is delivered multiple times
- **THEN** the order remains paid and points or membership are granted exactly once

#### Scenario: Browser returns from payment page
- **WHEN** the browser reaches a success-looking return URL before server confirmation
- **THEN** the UI displays “确认支付结果中” and does not issue entitlement

#### Scenario: Notification amount does not match order snapshot
- **WHEN** a signed notification contains a different amount or merchant order
- **THEN** the system rejects activation, records a redacted security event and initiates reconciliation

### Requirement: Checkout recovers from expiry and delayed notification
An expired QR SHALL not be reusable. The user SHALL be able to create a new payment action, while delayed official notifications remain idempotently associated with their original order.

#### Scenario: Dynamic QR expires unpaid
- **WHEN** the checkout expiry is reached without confirmed payment
- **THEN** the system closes or expires the payment action and offers a fresh official checkout

### Requirement: Refund uses the official provider and audited permissions
Refund requests SHALL use the server provider adapter, preserve order and entitlement audit history and update customer-visible status from verified provider results. Support users MUST NOT directly mark orders paid or refunded.

#### Scenario: Authorized refund succeeds
- **WHEN** a permitted refund workflow receives official provider confirmation
- **THEN** the order and affected entitlement move to the published refunded state exactly once

## REMOVED Requirements

### Requirement: Manual payment proof for new orders
**Reason**: Official provider orders, signed notifications and active queries replace transaction references, screenshots and manual payment approval.

**Migration**: Stop creating new manual-proof orders. Existing manual orders remain read-only and may complete their original audit/refund policy, but the new checkout does not expose proof-upload controls.

