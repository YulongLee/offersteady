## 1. Entitlement State and Formatting

- [x] 1.1 Add a Web adapter method that reads the existing authenticated billing-state endpoint and maps it to the current billing domain model.
- [x] 1.2 Add deterministic remaining-duration formatting and boundary tests for days, hours, minutes and expired entitlements.

## 2. Billing Experience

- [x] 2.1 Rename the application billing navigation entry to “积分与会员” without changing its route.
- [x] 2.2 Replace the points-only hero card with a responsive “我的权益” presentation for active, queued and absent membership states while retaining points and allowance information.
- [x] 2.3 Refresh trusted billing state after a confirmed payment and at membership expiry boundaries, including an explicit recoverable synchronization state.

## 3. Verification and Rollout

- [x] 3.1 Add Web regression coverage for active membership, queued extensions, no membership, expiry transitions and post-payment entitlement refresh.
- [x] 3.2 Run focused Web tests, full Web tests, type checking, production build and strict OpenSpec validation.
- [ ] 3.3 Deploy only the Web application and verify the production billing page on desktop and mobile widths without changing Backend or desktop companion releases.
