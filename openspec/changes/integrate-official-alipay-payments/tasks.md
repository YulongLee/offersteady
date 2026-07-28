## 1. Payment Provider Foundation

- [x] 1.1 Add server configuration for provider selection and official Alipay credentials
- [x] 1.2 Add an RSA2 Alipay computer-web checkout and notification adapter
- [x] 1.3 Keep the existing MZFPay adapter available for rollback and historical orders

## 2. Order and Callback Integration

- [x] 2.1 Persist the payment provider on every checkout order with a backward-compatible migration
- [x] 2.2 Route new checkout creation through the configured provider
- [x] 2.3 Add the official Alipay notify and browser-return endpoints
- [x] 2.4 Reject cross-provider callbacks before entitlement settlement

## 3. Product Experience and Operations

- [x] 3.1 Update checkout UI and order history to describe the actual payment provider
- [x] 3.2 Document Alipay server secrets, rollout configuration, and rollback behavior
- [x] 3.3 Add provider signing, identity validation, amount, and callback isolation regression tests
