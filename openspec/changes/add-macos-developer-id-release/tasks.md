## 1. Release configuration

- [x] 1.1 Add dedicated Developer ID electron-builder configuration with stable bundle ID, Hardened Runtime, explicit native binary signing, DMG target, and mandatory notarization.
- [x] 1.2 Split main and inherited minimal entitlements while preserving capture usage descriptions.
- [x] 1.3 Add fail-closed release and signed-prepare commands without changing local development commands.

## 2. Verification and secret safety

- [x] 2.1 Add a verifier for outer and nested signatures, identity/team, Hardened Runtime, timestamps, Gatekeeper, and stapled ticket.
- [x] 2.2 Extend `.gitignore` and tests to cover Apple API keys, certificates, provisioning profiles, and notary credential artifacts.
- [x] 2.3 Add release configuration regression tests for bundle ID, identity, entitlements, notarization, and command separation.

## 3. Documentation and build evidence

- [x] 3.1 Document App Store Connect API key and Keychain profile setup without committing credentials.
- [x] 3.2 Run desktop typecheck/tests/build and strict OpenSpec validation.
- [x] 3.3 Build and verify the Developer ID signed arm64 production App and DMG; require Accepted notarization, stapled tickets, and passing Gatekeeper assessments for both artifacts.
- [x] 3.4 Confirm no server deployment or website publication occurred.
- [x] 3.5 Build and verify the Developer ID signed Intel x64 production App and DMG; require x86_64 native components, Accepted App/DMG notarization, stapled tickets, and passing Gatekeeper assessments.
