## 1. Configuration and Data Model

- [x] 1.1 Add SMS authentication settings to backend config and `.env.example`, including provider mode, Aliyun endpoint/region, access key variables, sign name, template code, TTL, send interval, daily limit, and verification attempt limit.
- [x] 1.2 Add authentication repository records for phone identity binding and SMS challenge metadata without storing plaintext verification codes.
- [x] 1.3 Add PostgreSQL schema/migration support for users, phone identities, auth sessions, refresh token fingerprints, and SMS challenge audit records.
- [x] 1.4 Update `docs/environment-variables.md` with server-only Aliyun SMS variables and local integration guidance.

## 2. SMS Provider Adapter

- [x] 2.1 Define `SmsVerificationProviderPort` for sending verification codes and checking verification codes.
- [x] 2.2 Implement an Aliyun Dypnsapi provider that calls `SendSmsVerifyCode` and maps provider response ids, status, latency, and errors into internal result types.
- [x] 2.3 Implement Aliyun verification with `CheckSmsVerifyCode` and stable internal outcomes for success, invalid code, expired code, rate limited, and provider unavailable.
- [x] 2.4 Implement a fake SMS provider for unit tests and local development without real SMS delivery.
- [x] 2.5 Add provider probe/integration verification that can be explicitly enabled with real Aliyun credentials and a test phone number.

## 3. Backend Authentication Flow

- [x] 3.1 Add request/response schemas for SMS send-code and verify-login APIs with phone normalization, challenge id, cooldown, expiry, and safe error payloads.
- [x] 3.2 Implement `POST /api/v1/auth/sms/send-code` with phone validation, challenge creation, rate limiting, provider call, and redacted logging.
- [x] 3.3 Implement `POST /api/v1/auth/sms/verify-login` with challenge lookup, attempt limits, provider verification, auto-register-or-login, auth session issuance, and token response.
- [x] 3.4 Extend current user and identity binding responses to represent SMS/phone provider safely.
- [x] 3.5 Ensure refresh, logout, current-user, and protected API dependencies work for SMS-created sessions.

## 4. Frontend Login and Auth State

- [x] 4.1 Update `auth-client` to support `sendSmsCode`, `verifySmsLogin`, real session persistence, token refresh, logout, and current user restoration.
- [x] 4.2 Replace the primary login/register UI with phone + SMS code flow while preserving the current prototype layout language.
- [x] 4.3 Add cooldown timer, loading state, validation errors, provider failure state, and retry behavior for SMS code sending.
- [x] 4.4 Remove main-flow forced admin prototype identity fallback so unauthenticated users must log in before protected product pages load.
- [x] 4.5 Preserve a test-only or explicitly configured prototype identity path for local fixtures and automated tests.

## 5. Product Data Ownership Integration

- [x] 5.1 Audit material library, interview creation, billing/points, desktop binding, history, and profile APIs for hardcoded `admin` or prototype user assumptions.
- [x] 5.2 Route protected backend operations through authenticated user context so records are owned by the SMS-authenticated `userId`.
- [x] 5.3 Update frontend data loading to use the current authenticated account for materials, interviews, points, and session creation.
- [x] 5.4 Add logout/login switching behavior so two users on the same browser never see each other's materials, points, interviews, or history.

## 6. Tests and Verification

- [x] 6.1 Add backend unit tests for phone validation, send-code rate limiting, Aliyun/fake provider mapping, invalid/expired code handling, and auto-register-or-login.
- [x] 6.2 Add backend auth-session tests proving SMS-created sessions work with refresh, logout, `/me`, and protected API dependencies.
- [x] 6.3 Add frontend tests for SMS login UI states, successful login persistence, unauthenticated guard behavior, token refresh, and logout.
- [x] 6.4 Add integration verification docs and command coverage for fake provider mode and optional real Aliyun SMS probe.
- [x] 6.5 Run `openspec validate rebuild-sms-authentication-service --strict` and record any remaining implementation constraints before apply completion.
