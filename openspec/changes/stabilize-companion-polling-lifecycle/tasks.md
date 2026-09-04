## 1. Desktop lifecycle regression coverage

- [x] 1.1 Add a source-level regression test for profile-scoped Electron single-instance ownership and second-launch window focus
- [x] 1.2 Add unit tests for terminal screenshot admission classification, suspension, transient backoff and new-binding wakeup
- [x] 1.3 Add regression coverage proving binding polls remain single-flight and coalesce visibility wakeups

## 2. Desktop lifecycle implementation

- [x] 2.1 Claim the edition-profile single-instance lock before app readiness and exit duplicate processes before runtime loops start
- [x] 2.2 Implement terminal invalid-binding suspension without fallback polling while preserving transient failure recovery
- [x] 2.3 Wake one screenshot stream owner immediately when a new valid binding becomes eligible

## 3. Backend duplicate-read protection

- [x] 3.1 Verify and extend focused tests for identical active-connection singleflight/cache behavior, pinned-identity separation and mutation invalidation
- [x] 3.2 Keep successful active-connection duplicate reads bounded below the live refresh interval and expose privacy-safe aggregate diagnostics

## 4. Verification and release

- [x] 4.1 Run focused Desktop and Backend regression tests
- [x] 4.2 Run full Desktop and Backend tests, typechecks and production builds without including unrelated Global changes in the domestic artifact
- [x] 4.3 Run strict OpenSpec validation and record the executed verification
- [x] 4.4 Capture the current production rollback baseline and confirm active interviews are zero
- [x] 4.5 Package and publish domestic Companion 1.2.14 for supported platforms, deploy only required domestic services, and run public health/download/core smoke tests
- [x] 4.6 Compare privacy-safe request rate, ordinary API P95 and errors after rollout
