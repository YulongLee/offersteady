## 1. Authentication and provider foundation

- [x] 1.1 Define or extend backend auth domain models for internal users, provider identities, auth sessions, and safe current-user summaries
- [x] 1.2 Implement a provider-agnostic WeChat-compatible login adapter boundary, including authorization-session creation, callback verification, and one-time state validation
- [x] 1.3 Add configuration boundaries for development-compatible provider mode versus formal WeChat provider mode without exposing secrets to the client

## 2. Backend login flow and middleware

- [x] 2.1 Implement authorization-session, callback, token refresh, current-user, and logout APIs that preserve one internal User ID across repeated logins
- [x] 2.2 Implement first-login auto-registration, existing-identity reuse, duplicate-binding prevention, and auth-session issuance with JWT access token plus refresh token
- [x] 2.3 Add shared authentication middleware or dependency resolution so protected APIs consume authenticated User ID through one common boundary

## 3. Frontend login flow integration

- [x] 3.1 Wire the login page and WeChat authorization dialog to real authorization-session APIs while preserving the approved prototype route structure and interaction order
- [x] 3.2 Implement frontend handling for waiting, scanned, authorized, expired, failed, refresh, and successful-entry states without introducing testing-only product branches
- [x] 3.3 Implement client-side authenticated session restore, logout, and current-user loading against the backend authentication contract

## 4. User ownership binding across core modules

- [x] 4.1 Bind Resume, JD, Knowledge Base, Interview Session, Conversation, Screenshot, Speech, and History creation paths to the authenticated internal User ID
- [x] 4.2 Enforce cross-user isolation for core resource reads, writes, deletes, and history queries through shared ownership checks
- [x] 4.3 Verify that business modules use internal User ID instead of provider-native identity fields as the ownership key

## 5. Verification and documentation

- [x] 5.1 Add backend and frontend regression tests for successful login, expired authorization session, replayed callback rejection, logout, refresh, and current-user retrieval
- [x] 5.2 Add integration verification coverage for provider swap readiness and authenticated ownership isolation across at least one user-owned resource flow
- [x] 5.3 Update login and environment documentation for WeChat-compatible provider setup, callback handling, state expiration, and production cutover guidance, then run `openspec validate implement-wechat-login-service --strict`
