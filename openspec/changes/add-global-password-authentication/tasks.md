## 1. Password and challenge foundation

- [x] 1.1 Add Argon2id password hashing with legacy PBKDF2 verification and rehash support
- [x] 1.2 Add purpose-bound email challenge persistence through an additive migration and repository mappings
- [x] 1.3 Add Global password policy, generic authentication failures, and throttling configuration

## 2. Global customer authentication APIs

- [x] 2.1 Add verified registration and existing-account password-setup service flows
- [x] 2.2 Add Global email-and-password login with legacy hash upgrade
- [x] 2.3 Add forgotten-password send/complete and authenticated password-change flows with session revocation
- [x] 2.4 Expose Global-only API schemas and routes while preserving legacy email-code and domestic SMS behavior

## 3. Global Web experience

- [x] 3.1 Replace the Global customer default login UI and client calls with email and password
- [x] 3.2 Add Global registration, existing-account password setup, and forgotten-password UI states
- [x] 3.3 Add authenticated password change to Global account settings

## 4. Verification and release readiness

- [x] 4.1 Add Backend regression tests for registration, login, setup, recovery, policy, replay prevention, and session revocation
- [x] 4.2 Add Global Web tests for the password journeys and confirm domestic and Global Admin sources are unchanged
- [x] 4.3 Run targeted Backend/Web tests, builds, OpenSpec strict validation, and document Global migration and rollback checks
