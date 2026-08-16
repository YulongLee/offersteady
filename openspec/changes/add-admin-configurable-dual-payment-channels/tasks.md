## 1. Payment configuration persistence

- [x] 1.1 Add a migration for encrypted, versioned WeChat and Alipay channel configurations seeded disabled
- [x] 1.2 Add repository methods to read, save, validate-state, enable and disable payment channels atomically
- [x] 1.3 Add field-level encryption, masking and configuration completeness validation using the existing admin encryption key
- [x] 1.4 Add `payments.manage` RBAC and audit coverage without exposing secret values

## 2. Official provider adapters and checkout

- [x] 2.1 Refactor checkout provider resolution to use the requested enabled channel while preserving historical MZFPay orders
- [x] 2.2 Adapt official Alipay checkout and notifications to versioned database configuration
- [x] 2.3 Implement WeChat Pay API v3 Native signing, checkout response parsing, notification verification and resource decryption
- [x] 2.4 Keep channel shutdown non-destructive for existing pending orders and enforce cross-channel callback isolation
- [x] 2.5 Expose only enabled and ready payment channels in authenticated billing state

## 3. Administration and user interfaces

- [x] 3.1 Add guarded admin APIs for masked channel configuration, draft updates, validation and independent enable/disable actions
- [x] 3.2 Add an admin payment settings workspace with separate WeChat and Alipay readiness, secret replacement and activation controls
- [x] 3.3 Update the user billing page to support zero, one or two available official payment channels and accurate checkout actions
- [x] 3.4 Preserve current payment-disabled messaging and existing order history when no official channel is enabled

## 4. Verification and release safety

- [x] 4.1 Add backend tests for encryption, masking, RBAC, incomplete configuration, versioning and audit redaction
- [x] 4.2 Add synthetic Alipay and WeChat signing, callback, amount, duplicate-delivery and provider-mismatch tests
- [x] 4.3 Add Web and Admin tests for disabled, single-channel and dual-channel states
- [x] 4.4 Run backend, Web and Admin regression tests, production builds and strict OpenSpec validation
- [x] 4.5 Deploy migration and applications with both channels disabled, then verify existing public health, billing, account and interview flows
- [x] 4.6 Document merchant onboarding and the separate real small-value acceptance checklist required before enabling each channel

## 5. Production WeChat Native checkout regression

- [x] 5.1 Generate provider-compatible merchant order identifiers without breaking local idempotency or callback lookup
- [x] 5.2 Mark rejected provider checkouts failed and expose only safe WeChat error diagnostics
- [x] 5.3 Add regression tests for WeChat order constraints, rejected Native requests and failed-order persistence
- [x] 5.4 Run focused and full payment verification, deploy, and verify the production Native checkout reaches a real QR response
