## ADDED Requirements

### Requirement: Global product has no referral campaign
The Global application SHALL NOT display referral or invitation campaign controls, activate referral codes, or automatically request referral status.

#### Scenario: User opens Global billing
- **WHEN** a Global user opens the billing or account-plan route
- **THEN** no referral cards, invite rewards, referral statistics, or referral API requests are present

#### Scenario: User opens a legacy Global invitation URL
- **WHEN** a user opens a Global `/invite/:code` URL
- **THEN** the application returns the user to the normal public entry flow without activating or persisting the referral code

### Requirement: Global billing excludes domestic checkout
The Global billing surface SHALL show account credits, active entitlement, usage rules, and ledger history in English without rendering or invoking Alipay, WeChat Pay, QR checkout, or a domestic product catalogue.

#### Scenario: Global commerce is not configured
- **WHEN** a Global user opens billing before an international payment provider is configured
- **THEN** existing account and usage information remains available and no nonfunctional checkout action is offered

### Requirement: Future international checkout is provider-isolated
When international purchasing is enabled in a future change, checkout creation and payment confirmation MUST occur through a server-side provider adapter, secrets MUST remain server-side, and credits or entitlements MUST be granted only from a verified idempotent webhook event.

#### Scenario: Browser returns from checkout
- **WHEN** a user returns to OfferSteady after an international checkout
- **THEN** the redirect alone does not grant credits or entitlement and the UI reflects backend-confirmed order state

#### Scenario: Provider retries a webhook
- **WHEN** the same verified payment event is delivered more than once
- **THEN** the system applies the credit or entitlement exactly once

### Requirement: Domestic commerce remains isolated
Changes to Global referral and commerce presentation MUST NOT alter the Chinese application's referral, payment, balance, entitlement, or ledger behavior.

#### Scenario: Global release is prepared
- **WHEN** the Global commerce-boundary change is verified or deployed
- **THEN** Chinese Web regression checks pass and no Chinese production service is restarted by the Global deployment

