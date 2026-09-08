## ADDED Requirements

### Requirement: Checkout is created by the Global Backend
The Global Backend SHALL create Creem checkout sessions from authenticated user identity, internal offer code, server-owned active plan version, and idempotency key. Creem credentials and authoritative product mappings MUST remain server-side.

#### Scenario: Customer starts a valid purchase
- **WHEN** an authenticated Global customer selects an active paid offer while commerce is enabled
- **THEN** the Backend persists one pending internal order, creates or reuses one Creem checkout, and returns only the safe checkout URL and internal order state

#### Scenario: Browser submits a different price or product
- **WHEN** a request includes a client price, currency, duration, benefit, or provider product identifier
- **THEN** the Backend ignores it as authority and uses the active server-owned plan and validated mapping

#### Scenario: Retry repeats checkout creation
- **WHEN** the same user repeats a checkout request with the same idempotency key
- **THEN** the system returns the same internal order/checkout outcome without creating a second payable order

### Requirement: Checkout activation fails closed
New checkout creation SHALL remain disabled unless the Global edition, provider mode, environment secrets, active mappings, provider product validation, webhook acceptance, legal links, and explicit operator activation are all ready.

#### Scenario: Any readiness gate is missing
- **WHEN** a customer attempts checkout while one activation gate is not satisfied
- **THEN** the service creates no provider checkout and returns a safe unavailable state without exposing configuration details

#### Scenario: New checkout is disabled after configuration change
- **WHEN** an operator changes a plan mapping or payment configuration
- **THEN** new checkout creation is disabled until validation succeeds again while historical webhook and reconciliation processing remains available

### Requirement: Webhook authenticity and business facts are verified
The webhook endpoint MUST verify the `creem-signature` against the exact raw request body using HMAC-SHA256 and constant-time comparison, then validate environment, event type, internal reference, provider product, customer, currency, amount, and payment/subscription status before fulfillment.

#### Scenario: Signature is invalid
- **WHEN** a webhook signature is missing or does not match
- **THEN** no order, subscription, entitlement, or usage state changes and a redacted security diagnostic is recorded

#### Scenario: Payment facts do not match the order
- **WHEN** a signed event has a mismatched product, customer, currency, amount, mode, or internal reference
- **THEN** fulfillment fails closed, the order is flagged for reconciliation, and no value is granted

### Requirement: Provider events are idempotent and order-independent
The system SHALL persist each provider event ID once and apply event, order, subscription, and entitlement mutations in one transaction. Duplicate and reordered events MUST converge without duplicate access or credits.

#### Scenario: Creem retries the same event
- **WHEN** the same signed provider event is delivered multiple times
- **THEN** the first successful transaction is retained and later deliveries return success without granting value again

#### Scenario: Subscription events arrive out of order
- **WHEN** an older subscription event arrives after a newer effective state
- **THEN** the system records the event but does not regress the confirmed subscription period or entitlement

### Requirement: Provider lifecycle controls access
One-time access SHALL be fulfilled from a verified completed checkout; recurring access SHALL be fulfilled or renewed from verified paid subscription periods. Cancellation, pause, expiry, refund, and dispute behavior SHALL use provider-confirmed effective state and immutable internal history.

#### Scenario: Monthly subscription renews
- **WHEN** a verified `subscription.paid` event confirms a new monthly period
- **THEN** the system grants that period exactly once and records the provider subscription and transaction references

#### Scenario: Subscription cancels at period end
- **WHEN** cancellation is confirmed for the end of a paid period
- **THEN** access remains until the confirmed period end and no later period is granted without payment

#### Scenario: Refund or dispute is confirmed
- **WHEN** a verified refund or dispute event applies to a fulfilled order
- **THEN** the system records the financial reversal and applies the approved remaining-entitlement policy without deleting history or creating a fabricated negative usage balance

### Requirement: Redirects never grant access
The checkout success/return route SHALL be informational and SHALL derive displayed state from the internal Backend order. Query parameters, browser redirects, and client polling MUST NOT grant or renew an entitlement.

#### Scenario: Customer opens a forged success URL
- **WHEN** a browser opens the return route with plausible provider identifiers but no verified fulfillment
- **THEN** no value is granted and the page shows the actual pending, failed, or unknown internal state

### Requirement: Customers can manage recurring billing safely
The Global Backend SHALL create short-lived Creem customer-portal access for the authenticated owner and SHALL synchronize subscription changes from verified provider events.

#### Scenario: Monthly subscriber opens billing management
- **WHEN** the authenticated subscription owner requests management access
- **THEN** the Backend returns a provider portal URL without exposing API credentials or another customer's identifier

### Requirement: Reconciliation repairs missed delivery
An authorized reconciliation process SHALL query provider truth for pending or inconsistent orders/subscriptions and apply the same validation and idempotent fulfillment path as webhooks.

#### Scenario: Webhook delivery was missed
- **WHEN** reconciliation finds a provider-confirmed paid transaction that has not been fulfilled
- **THEN** the system verifies all business facts and grants the entitlement exactly once
