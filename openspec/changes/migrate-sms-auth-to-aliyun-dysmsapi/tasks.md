## 1. Configuration and Persistence

- [x] 1.1 Add explicit Dysmsapi provider configuration and a required server-only verification-code pepper.
- [x] 1.2 Add a nullable challenge code digest migration and repository mappings without exposing plaintext codes.

## 2. Provider Implementation

- [x] 2.1 Implement secure six-digit code generation, `Dysmsapi SendSms`, response mapping, and digest return.
- [x] 2.2 Implement constant-time local verification while preserving existing Dypnsapi and fake providers.
- [x] 2.3 Wire production provider gates and integration diagnostics for `aliyun-dysmsapi`.

## 3. Verification and Release

- [x] 3.1 Add regressions for request shape, digest-only persistence, valid/invalid/expired codes, and provider rollback.
- [x] 3.2 Update environment documentation and examples for both Aliyun SMS modes.
- [x] 3.3 Run backend tests and strict OpenSpec validation.
- [ ] 3.4 Deploy the new backend and database migration, then run one authorized production SMS send/verify smoke test. (Deployment and real send passed; final user-entered production verification remains.)
