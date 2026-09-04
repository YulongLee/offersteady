## 1. Data model and configuration

- [x] 1.1 Add additive partner, reward-claim, commission-ledger and payout-request migration with constraints and indexes
- [x] 1.2 Add default-off partner program configuration and production validation

## 2. Backend domain and persistence

- [x] 2.1 Implement partner repository enrollment, stable link and aggregate dashboard operations
- [x] 2.2 Implement idempotent paid-order projection, refund reversal and observation-period balances
- [x] 2.3 Implement atomic monthly payout requests and audited state transitions
- [x] 2.4 Enforce mutual exclusion between cash partner attribution and points referral activation

## 3. Backend APIs and operations

- [x] 3.1 Add authenticated user partner status, join and payout request APIs
- [x] 3.2 Add permission-protected partner, projection, adjustment and payout admin APIs
- [x] 3.3 Integrate bounded commission projection with the existing promotion analytics worker without changing hot paths

## 4. User and admin experience

- [x] 4.1 Add the homepage Footer entry, partner route and responsive join/dashboard experience
- [x] 4.2 Add partner and settlement management to the existing admin promotion center
- [x] 4.3 Keep disabled and unavailable states explicit without exposing referred-user personal information

## 5. Verification and documentation

- [x] 5.1 Add backend regression tests for enrollment, link stability, eligibility, idempotency, reversals, payout concurrency and reward mutual exclusion
- [x] 5.2 Add Web and Admin tests for entry, aggregate metrics, disabled state and settlement actions
- [x] 5.3 Run backend tests, frontend tests/typechecks/builds and strict OpenSpec validation
- [x] 5.4 Document operational defaults, manual refund/settlement SOP, rollout and rollback boundaries
