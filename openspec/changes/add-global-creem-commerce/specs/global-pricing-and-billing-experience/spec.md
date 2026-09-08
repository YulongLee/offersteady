## ADDED Requirements

### Requirement: Global pricing is clear and comparable
The Global customer experience SHALL present the five approved offers in concise English with price, USD denomination, one-time or recurring billing, duration, Copilot allowance, Screen Assist allowance, material access, featured state, and Fair Use link.

#### Scenario: Customer compares offers
- **WHEN** the Global pricing page loads
- **THEN** Free, Interview Day Pass, Pro Weekly, Pro Monthly, and Job Hunt have distinct benefits and Pro Weekly is visually identified as the recommended starting offer

#### Scenario: Customer views a recurring offer
- **WHEN** Pro Monthly is presented before checkout
- **THEN** the UI clearly states `$99.99 USD per month`, automatic renewal until canceled, and how to manage the subscription

#### Scenario: Customer views a one-time offer
- **WHEN** Interview Day Pass, Pro Weekly, or Job Hunt is presented
- **THEN** the UI explicitly states one-time purchase and the exact access duration without suggesting automatic renewal

### Requirement: Final price expectations are disclosed
The pricing and checkout handoff SHALL identify displayed prices as USD base prices and SHALL tell customers that Creem shows final local currency and applicable tax before payment.

#### Scenario: Customer proceeds from the UK, Australia, Canada, or US
- **WHEN** the customer selects a paid offer
- **THEN** the handoff explains that the provider checkout is authoritative for final currency/tax and does not claim an unverified tax-inclusive amount

### Requirement: Checkout has safe customer states
The Global UI SHALL show disabled, creating, redirected, pending confirmation, paid, failed, expired, refunded, disputed, and retryable states from Backend order truth without blocking access to existing valid entitlements.

#### Scenario: Payment confirmation is delayed
- **WHEN** the customer returns before a verified webhook is processed
- **THEN** the UI shows `Confirming payment` and refreshes boundedly without claiming access was granted

#### Scenario: Provider is temporarily unavailable
- **WHEN** checkout creation fails safely
- **THEN** the UI preserves current account access, prevents duplicate rapid submissions, and provides a retry/support path

### Requirement: Customers can understand their entitlement
The Global account page SHALL show current plan, effective period, Copilot minutes remaining when metered, Screen Assist uses remaining when metered, Unlimited state, included material features, billing history, and provider-confirmed subscription status.

#### Scenario: Interview Day Pass customer opens account
- **WHEN** a customer has an active Interview Day Pass
- **THEN** the account displays its expiry, remaining Copilot minutes, Unlimited Screen Assist, and Resume/JD access

#### Scenario: Unlimited customer opens account
- **WHEN** a customer has an active Pro entitlement
- **THEN** the account displays Unlimited without inventing a hidden minute balance and links to the Fair Use policy

### Requirement: Monthly subscribers can manage renewal
Active Pro Monthly customers SHALL have a secure `Manage subscription` action that obtains a short-lived Backend-created customer-portal URL. Cancellation state and access end date SHALL come from provider-confirmed Backend state.

#### Scenario: Customer cancels renewal
- **WHEN** Creem confirms cancellation at the end of the paid period
- **THEN** the UI shows `Cancels on <date>` and access continues through that date

### Requirement: Purchase UX is accessible and responsive
Pricing cards, comparison content, checkout states, billing history, policy links, and primary actions SHALL remain usable by keyboard and screen reader and at supported desktop, tablet, and mobile widths.

#### Scenario: Mobile customer compares plans
- **WHEN** the pricing page is rendered at a narrow supported width
- **THEN** prices, renewal terms, benefits, policies, and purchase actions remain readable without horizontal page scrolling or clipped controls

### Requirement: Domestic purchase UX remains unchanged
Global pricing and Creem behavior SHALL not alter Chinese pricing, domestic payment channels, referrals, account state, or checkout components.

#### Scenario: Global release candidate is verified
- **WHEN** Global commerce UI is built or tested
- **THEN** Chinese Web billing/payment regression tests pass and no Creem asset, route, or label appears in the Chinese customer bundle
