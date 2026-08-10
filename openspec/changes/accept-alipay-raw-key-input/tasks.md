## 1. Backend Key Normalization

- [x] 1.1 Add synthetic regressions for raw Base64, full PEM, invalid material, non-RSA keys and existing saved drafts.
- [x] 1.2 Normalize valid Alipay RSA private/public keys to canonical PEM before validation and encrypted persistence.

## 2. Admin Guidance

- [x] 2.1 Update Alipay secret field guidance to state that copied raw key text and PEM are both accepted without exposing saved values.

## 3. Verification and Rollout

- [x] 3.1 Run focused and full Backend/Admin tests, production builds and strict OpenSpec validation.
- [ ] 3.2 Commit, push and deploy only affected Backend/Admin services, then verify production health and configuration revalidation.
