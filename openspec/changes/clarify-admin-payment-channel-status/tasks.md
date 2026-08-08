## 1. Payment status presentation

- [x] 1.1 Add typed payment-channel status derivation for configuration readiness, user availability, labels and explanatory copy
- [x] 1.2 Redesign each Admin payment card with prominent usage and configuration status badges, version/update metadata and field-level validation guidance
- [x] 1.3 Replace the activation button with an accessible, confirmed on/off switch that remains disabled until configuration is ready

## 2. Authentication recovery

- [x] 2.1 Normalize expired Admin session and recent-MFA errors without exposing internal error codes in the payment workspace
- [x] 2.2 Route payment save and activation authentication failures back through the Admin login flow while keeping merchant secrets out of browser persistence

## 3. Verification and release

- [x] 3.1 Add Admin unit tests covering draft, ready-disabled, ready-enabled and authentication-failure states
- [x] 3.2 Update payment operations documentation to distinguish saved, ready, enabled and real-payment-verified states
- [x] 3.3 Run Admin tests/build, strict OpenSpec validation and repository checks
- [x] 3.4 Deploy only the Admin static application and verify the production payment status page without changing Backend, Web or payment records
