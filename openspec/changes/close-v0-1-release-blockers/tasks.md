## 1. Contract

- [x] 1.1 Define release database, E2E, security and desktop diagnostic gates.

## 2. Backend and database

- [x] 2.1 Add idempotent pgvector extension migration and repository initialization.
- [x] 2.2 Fix E2E token inheritance and remove stale static findings.
- [x] 2.3 Add realtime ASR verification dependency to the production image.

## 3. Web and desktop

- [x] 3.1 Upgrade vulnerable production routing dependencies.
- [x] 3.2 Add production web and API security response headers.
- [x] 3.3 Make native zero-frame diagnostics fail and stabilize the desktop Bundle ID.

## 4. Verification and release

- [x] 4.1 Run workspace tests, backend regression, database/provider/E2E tests and dependency audit.
- [x] 4.2 Build Web and macOS ARM64 release artifacts and validate expected signing limitation.
- [ ] 4.3 Back up production, deploy, enable pgvector and verify public security headers.
