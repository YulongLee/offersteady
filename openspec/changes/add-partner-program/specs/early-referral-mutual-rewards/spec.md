## ADDED Requirements

### Requirement: Cash partner and points referral rewards do not stack
Every newly acquired user SHALL have at most one reward program claim: `cash_partner` or `points_referral`. A successful claim under one program MUST make later activation under the other program ineligible, while retries of the same claim remain idempotent.

#### Scenario: Partner-attributed user tries to activate points referral
- **WHEN** a user's acquisition has been locked to a cash partner and the user submits an invitation-points activation
- **THEN** the system rejects the points activation without changing the partner attribution or issuing points

#### Scenario: Points referral already activated before partner claim
- **WHEN** a user already has a successful points referral activation and later opens or claims a partner link
- **THEN** the visit may remain in aggregate analytics but the user and their orders are ineligible for partner cash commission

#### Scenario: Same reward claim is retried
- **WHEN** the same acquisition claim is retried after success
- **THEN** the system returns the original reward-program outcome without issuing duplicate value
