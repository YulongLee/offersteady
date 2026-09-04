## ADDED Requirements

### Requirement: Reconciliation exposes complete aggregate states
The administrator partner view SHALL show counts and monetary totals for eligible paid orders, refund-hold pending commission, available commission, payout-reserved commission, paid commission, refund reversals and negative carry-forward. Monetary values MUST be derived from authoritative orders and the append-only commission ledger.

#### Scenario: Administrator opens partner reconciliation
- **WHEN** an active administrator opens “推广中心 → 合作伙伴”
- **THEN** the page shows current aggregate order and commission states with data freshness and rule-version context

### Requirement: Administrators can reconcile order-level commission without referred-user PII
The administrator view SHALL provide a bounded paginated commission-order table containing order reference, partner slug, net receipt, commission amount, paid time, eligibility time, refund amount, ledger state and settlement reference. It MUST NOT expose referred-user phone numbers, interview content, audio, screenshots, materials or browsing timelines.

#### Scenario: Finance filters unsettled orders
- **WHEN** an administrator filters for available or reserved commission orders in a date range
- **THEN** the API returns only matching rows within the page limit and includes a stable next-page cursor or offset

#### Scenario: Order has a refund reversal
- **WHEN** an earning has one or more authoritative refund reversals
- **THEN** the row displays original earning, total reversal, net commission and current reconciliation state without deleting the original entry

### Requirement: Settlement operations show payout lifecycle and target status
The administrator view SHALL show settlement period, amount, masked payout method, request status, request/approval/payment timestamps, payment reference and linked order/ledger totals. Sensitive actions SHALL remain limited to `promotion.payout.manage` and recent MFA where required.

#### Scenario: Administrator reviews a pending payout
- **WHEN** a partner has submitted a monthly settlement request
- **THEN** the request appears in the pending filter with its reserved amount, masked payout target and reconciliation totals

#### Scenario: Administrator completes manual payment
- **WHEN** an authorized administrator marks an approved request paid with a non-sensitive external payment reference
- **THEN** the request moves to paid, settled totals update from the append-only ledger and the transition remains auditable

### Requirement: Reconciliation cannot degrade product hot paths
Reconciliation reads, filters and projection controls SHALL use independent bounded database concurrency, query timeouts and pagination. Failures or slow queries MUST NOT block registration, checkout, payment callbacks, interviews, ASR, answers or screenshots.

#### Scenario: Reconciliation query times out
- **WHEN** an administrator requests a report that exceeds its query budget
- **THEN** only that report returns a retryable unavailable state and all user-facing product flows continue normally
