## 1. Version Selection

- [x] 1.1 Add a pure helper that normalizes device target metadata, compares supported version strings, and selects the newest matching downloadable release.
- [x] 1.2 Add unit tests for older, equal, newer, suffixed, malformed, missing and platform/architecture mismatch cases.

## 2. Preparation Experience

- [x] 2.1 Show a compact non-blocking update reminder after successful device binding in both interview and written-exam preparation flows.
- [x] 2.2 Support matching download and continue-current-version actions without changing readiness or start behavior.
- [x] 2.3 Add preparation-page regression tests covering display, dismissal, no-warning fallback and unchanged binding request counts.

## 3. Verification and Release

- [x] 3.1 Run focused Web tests, the full Web test suite, type/build checks and strict OpenSpec validation.
- [x] 3.2 Record the production deployment gate, rollback reference and post-deployment verification evidence.
