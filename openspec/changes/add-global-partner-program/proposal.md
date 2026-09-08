## Why

OfferSteady Global needs the same first-level partner growth loop as the Chinese product so customers can share a dedicated link, understand attributed results and earn a transparent 20% commission. The Global implementation must remain operationally and financially isolated from the Chinese product and must not pretend that paid commission exists while Creem checkout is still disabled or unconfirmed.

## What Changes

- Add a prominent English `Partner Program` entry near the bottom of the public Global homepage; do not add it to the authenticated workbench navigation or interview workspace.
- Give each verified Global user one durable referral link and a private English dashboard for qualified visits, registrations, confirmed paid customers, attributed revenue, pending commission, available commission and settled commission.
- Attribute registrations and later Creem orders to the partner link without trusting browser redirects. Create commission only from provider-confirmed eligible USD receipts and append refund, dispute and chargeback reversals instead of rewriting history.
- Use a 20% commission rate, a configurable attribution/eligibility window and a refund observation period. Public homepage copy remains concise; detailed calculation and prohibited self-referral rules stay on the program page.
- Add a Chinese Global-admin operations area with a runtime activity switch, partner-level balances, order-level reconciliation, settlement requests and manual approve/reject/mark-paid controls.
- Keep the first release manual-settlement only. Store only the minimum encrypted international payout identifier through configurable methods such as PayPal or Wise; do not collect bank-card or identity-document data and do not claim automatic payout.
- Keep the activity enabled or disabled independently in Global production. Disabling hides public discovery and blocks new enrollment while preserving historical attribution, commissions and settlements.
- Do not modify or deploy the Chinese Web, Chinese Admin, Chinese database, domestic partner program, interviews, Companion, ASR, RAG, AI or screenshot-answer behavior.
- Before implementation, capture the currently deployed Global source as a Git-tracked rollback baseline because the existing Global application files are not yet committed in the current repository checkout.

## Capabilities

### New Capabilities

- `global-partner-program`: Global homepage discovery, verified-user enrollment, durable partner links, registration/Creem attribution, commission ledger, reversals and private partner dashboard.
- `global-partner-settlement-operations`: Encrypted minimal payout profiles, manual monthly settlement lifecycle, Chinese operator reconciliation, permissions, audit and runtime activity control.

### Modified Capabilities

None. The capability consumes provider-confirmed Global commerce facts without changing the existing Global catalogue, entitlement or checkout contracts.

## Impact

- Global Web (`apps/web-global`): public homepage entry and protected English partner dashboard.
- Shared Backend in Global edition only: new Global-scoped partner APIs, attribution projection, append-only USD commission ledger and settlement operations.
- Global operator console (`admin.offersteady.com`): Chinese partner controls and reconciliation views.
- Global PostgreSQL: additive Global-only tables and indexes; no domestic-table reuse.
- Creem integration: read provider-confirmed order/refund/dispute facts after commerce activation; no commission is generated from a browser success redirect.
- Operations: Global-specific feature gate, encryption key, monitoring, backup and rollback documentation.
