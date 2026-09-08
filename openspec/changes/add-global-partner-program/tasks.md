## 1. Global baseline and release isolation

- [ ] 1.1 Inventory the currently deployed overseas commit, images, schema state and rollback commands without changing either production environment
- [ ] 1.2 Review and commit the existing untracked Global application, commerce, deployment and OpenSpec files as a tested rollback baseline
- [ ] 1.3 Create an isolated implementation worktree and prove Chinese Web/Admin/Backend files and production configuration remain unchanged

## 2. Global partner persistence and accounting

- [ ] 2.1 Add Global-only runtime settings, partner profiles, attribution claims, append-only USD commission ledger, payout-profile versions and settlement-request migrations
- [ ] 2.2 Add indexes, uniqueness constraints, immutable-ledger guards and idempotency constraints for visits, registrations, Creem events, reversals and payouts
- [ ] 2.3 Implement dedicated Global payout encryption, masking and production fail-closed validation without storing banking or identity-document data
- [ ] 2.4 Add migration and repository tests for edition isolation, one-link identity, immutable accounting, payout versioning and retry idempotency

## 3. Attribution and Creem commission projection

- [ ] 3.1 Add qualified Global referral landing, first-party attribution and verified-email registration binding with self-referral and recursive-attribution protection
- [ ] 3.2 Project commission only from signed provider-confirmed eligible Creem receipts outside the synchronous checkout, webhook and interview hot paths
- [ ] 3.3 Add capped append-only refund, dispute and chargeback reversals plus negative carry-forward handling
- [ ] 3.4 Add synthetic tests for disabled commerce, fake redirects, duplicate/reordered events, partial/full reversals and domestic data isolation

## 4. Global customer experience

- [ ] 4.1 Add the concise English Partner Program section to the Global homepage bottom behind the runtime switch
- [ ] 4.2 Add the protected English enrollment and dashboard route with link copy, aggregate metrics, balance states, rules and settlement history
- [ ] 4.3 Add configurable PayPal/Wise payout-profile UI with masked saved state and explicit manual-settlement wording
- [ ] 4.4 Verify desktop/mobile accessibility and prove no partner entry or load is added to the workbench and live interview navigation

## 5. Global administration and manual settlement

- [ ] 5.1 Add Chinese Global-admin runtime switch, per-partner balance breakdown and order-level commission/reversal reconciliation
- [ ] 5.2 Add settlement-request approve, reject, release and mark-paid state transitions with immutable ledger entries and payment references
- [ ] 5.3 Add single-request payout-detail reveal guarded by payout permission, recent MFA, no-store responses and immutable audits
- [ ] 5.4 Add bounded query, pagination, authorization, masking, error-state and duplicate-payment regression tests

## 6. Verification and dormant rollout

- [ ] 6.1 Run Global Backend/Web/Admin tests, typechecks, builds, security/copy audits and strict OpenSpec validation using only synthetic data
- [ ] 6.2 Run Chinese Web/Admin/Backend regression and source-boundary checks and confirm no domestic release artifact changes
- [ ] 6.3 Confirm payout methods, minimum threshold, commission financial basis and English agreement text before enabling recruitment
- [ ] 6.4 Deploy only to the overseas Compose project with the activity disabled and verify health, attribution, dashboard, admin and rollback
- [ ] 6.5 Enable Global recruitment only after explicit approval; keep financial projection dormant until real Creem signed-event acceptance passes
