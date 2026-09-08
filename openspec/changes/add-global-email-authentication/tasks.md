## 1. Backend Contract and Persistence

- [x] 1.1 Add email identity and challenge contracts plus request/response schemas without changing SMS contracts
- [x] 1.2 Add additive PostgreSQL and in-memory repository support for email challenges

## 2. Delivery and Authentication Service

- [x] 2.1 Add fake and SMTP email provider adapters with secret-safe code verification and production fail-closed settings
- [x] 2.2 Implement email send and verify service flows, abuse limits, normalized account creation, and existing-account sign-in
- [x] 2.3 Expose Global email authentication endpoints and dependency wiring while keeping email disabled by default

## 3. Global Web Experience

- [x] 3.1 Add typed email send/verify API client methods and email account binding support to shared protocol types
- [x] 3.2 Replace only the Global Web phone form with an English email-code form and complete UI states

## 4. Verification and Operations

- [x] 4.1 Add Backend regression tests for success, reuse, invalid/expired/consumed codes, limits, and production configuration failure
- [x] 4.2 Add Global Web tests for email validation, send, cooldown, verify, and absence of the customer phone flow
- [x] 4.3 Document server-only email variables, provider activation checks, migration, rollback, and deliverability smoke tests
- [x] 4.4 Run OpenSpec strict validation and relevant Backend and Global Web checks without deploying to production

## 5. Global Production Activation

- [x] 5.1 Reuse the server-side OneShow SMTP transport without exposing credentials and generate an independent OfferSteady code pepper
- [x] 5.2 Deploy the isolated Global stack, apply the additive migration, and verify health, configuration shape, and invalid-email contract
- [x] 5.3 Confirm the domestic site and existing OneShow services remain healthy after Global activation
