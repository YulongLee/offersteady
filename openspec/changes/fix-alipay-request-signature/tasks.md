## 1. Signature Regression and Fix

- [x] 1.1 Add independent request-signature regressions that require `sign_type=RSA2` coverage while preserving notification verification.
- [x] 1.2 Separate outbound-request and notification canonicalization and use the correct function at each signing boundary.

## 2. Verification and Rollout

- [x] 2.1 Run focused and full Backend tests plus strict OpenSpec validation.
- [ ] 2.2 Commit, push and deploy only Backend, then verify production health and a newly generated checkout reaches the Alipay gateway without `invalid-signature`.
